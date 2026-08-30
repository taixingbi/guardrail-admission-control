from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class AcquireResult:
    ok: bool
    reason: str
    waited_s: float = 0.0


class StrongLimiter:
    """ApplyGuardrail inflight + gateway safety-budget token bucket (Bg), with tenant floors."""

    def __init__(
        self,
        inflight_limit: int,
        queue_max: int,
        *,
        reserved_share: dict[str, float] | None = None,
        overflow_mode: str = "reject",
        rg_rps: float | None = None,
        bg_rps: float | None = None,
        burst: int = 1,
    ) -> None:
        self._limit = max(int(inflight_limit), 1)
        self._queue_max = max(int(queue_max), 0)
        mode = str(overflow_mode or "reject").strip().lower()
        if mode not in {"queue", "reject"}:
            raise ValueError(f"unknown overflow_mode: {overflow_mode}")
        self._overflow_mode = mode
        self._reserved_share = dict(reserved_share or {})
        rate = bg_rps if bg_rps is not None else rg_rps
        self._rg_rps = float(rate) if rate and rate > 0 else None
        self._burst = max(int(burst), 1)
        self._shared_tokens = float(self._burst)
        self._reserved_tokens: dict[str, float] = {
            tid: float(self._burst) if float(frac or 0) > 0 else 0.0
            for tid, frac in dict(reserved_share or {}).items()
        }
        self._last_refill = time.monotonic()
        self._inflight = 0
        self._waiting = 0
        self._tenant_waiting: dict[str, int] = defaultdict(int)
        self._tenant_inflight: dict[str, int] = defaultdict(int)
        self._present: set[str] = set()
        self._cond = asyncio.Condition()

    @property
    def inflight(self) -> int:
        return self._inflight

    @property
    def waiting(self) -> int:
        return self._waiting

    @property
    def limit(self) -> int:
        return self._limit

    def estimated_wait_ms(self, tenant: str | None = None) -> float:
        if not self._rg_rps:
            return 0.0
        if tenant:
            self._refill()
            if self._rate_ok(tenant):
                return 0.0
            share = max(0.0, float(self._reserved_share.get(tenant, 0.0) or 0.0))
            rate = self._rg_rps * share if share > 0 else self._rg_rps
            if rate <= 0:
                return (self._waiting / self._rg_rps) * 1000.0
            tokens = self._reserved_tokens.get(tenant, 0.0)
            return max(0.0, (1.0 - tokens) / rate) * 1000.0
        return (self._waiting / self._rg_rps) * 1000.0

    def strong_available(self, tenant: str) -> bool:
        self._present.add(tenant)
        return self._can_admit(tenant)

    def reserved_slots(self, tenant: str) -> int:
        share = float(self._reserved_share.get(tenant, 0.0) or 0.0)
        if share <= 0:
            return 0
        return max(1, round(share * self._limit))

    def _shared_cap(self) -> int:
        reserved = sum(self.reserved_slots(t) for t in self._reserved_share)
        return max(0, self._limit - reserved)

    def _reserved_used(self) -> int:
        used = 0
        for tenant, n in self._tenant_inflight.items():
            used += min(n, self.reserved_slots(tenant))
        return used

    def _refill(self) -> None:
        if self._rg_rps is None:
            return
        now = time.monotonic()
        dt = now - self._last_refill
        self._last_refill = now
        reserved_frac = sum(max(0.0, float(f or 0)) for f in self._reserved_share.values())
        shared_rate = self._rg_rps * max(0.0, 1.0 - reserved_frac)
        self._shared_tokens = min(self._burst, self._shared_tokens + dt * shared_rate)
        for tid, frac in self._reserved_share.items():
            f = max(0.0, float(frac or 0))
            if f <= 0:
                continue
            self._reserved_tokens[tid] = min(
                self._burst, self._reserved_tokens.get(tid, 0.0) + dt * self._rg_rps * f
            )

    def _idle(self, tenant: str) -> bool:
        # Once a tenant has appeared in this cell, unused reserved tokens stay
        # theirs. Idle steal is only for tenants that never showed up (E1 A-only).
        if tenant in self._present:
            return False
        return self._tenant_waiting[tenant] == 0 and self._tenant_inflight[tenant] == 0

    def _rate_ok(self, tenant: str) -> bool:
        if self._rg_rps is None:
            return True
        self._refill()
        if self._reserved_tokens.get(tenant, 0.0) >= 1.0:
            return True
        if self._shared_tokens >= 1.0:
            return True
        return any(
            other != tenant
            and tok >= 1.0
            and self._idle(other)
            for other, tok in self._reserved_tokens.items()
        )

    def _take_rate(self, tenant: str) -> None:
        if self._rg_rps is None:
            return
        if self._reserved_tokens.get(tenant, 0.0) >= 1.0:
            self._reserved_tokens[tenant] -= 1.0
            return
        if self._shared_tokens >= 1.0:
            self._shared_tokens -= 1.0
            return
        for other, tok in self._reserved_tokens.items():
            if other != tenant and tok >= 1.0 and self._idle(other):
                self._reserved_tokens[other] -= 1.0
                return

    def _tenant_ok(self, tenant: str) -> bool:
        if self._inflight >= self._limit:
            return False
        reserved = self.reserved_slots(tenant)
        held = self._tenant_inflight[tenant]
        if held < reserved:
            return True
        shared_used = max(0, self._inflight - self._reserved_used())
        return shared_used < self._shared_cap()

    def _can_admit(self, tenant: str) -> bool:
        return self._rate_ok(tenant) and self._tenant_ok(tenant)

    def _take(self, tenant: str) -> None:
        self._take_rate(tenant)
        self._inflight += 1
        self._tenant_inflight[tenant] += 1

    async def acquire(self, tenant: str, timeout_s: float | None = None) -> AcquireResult:
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        async with self._cond:
            self._present.add(tenant)
            if self._overflow_mode == "reject":
                if not self._can_admit(tenant):
                    return AcquireResult(ok=False, reason="strong_full")
                self._take(tenant)
                return AcquireResult(ok=True, reason="admitted", waited_s=loop.time() - t0)
            if not self._can_admit(tenant) and self._waiting >= self._queue_max:
                return AcquireResult(ok=False, reason="queue_full")
            self._waiting += 1
            self._tenant_waiting[tenant] += 1
            try:
                while True:
                    if self._can_admit(tenant):
                        self._take(tenant)
                        return AcquireResult(ok=True, reason="admitted", waited_s=loop.time() - t0)
                    token_wait = 0.05 if self._rg_rps else None
                    if timeout_s is None and token_wait is None:
                        await self._cond.wait()
                        continue
                    remaining = None if timeout_s is None else timeout_s - (loop.time() - t0)
                    if remaining is not None and remaining <= 0:
                        return AcquireResult(ok=False, reason="queue_timeout", waited_s=loop.time() - t0)
                    waits = [w for w in (remaining, token_wait) if w is not None]
                    slice_s = min(waits) if waits else 0.05
                    try:
                        await asyncio.wait_for(self._cond.wait(), timeout=max(slice_s, 0.001))
                    except TimeoutError:
                        continue
            finally:
                self._waiting -= 1
                self._tenant_waiting[tenant] = max(0, self._tenant_waiting[tenant] - 1)

    async def release(self, tenant: str) -> None:
        async with self._cond:
            self._inflight = max(0, self._inflight - 1)
            self._tenant_inflight[tenant] = max(0, self._tenant_inflight[tenant] - 1)
            self._cond.notify_all()
