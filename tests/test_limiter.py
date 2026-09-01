import asyncio

from gasc.limiter import StrongLimiter


def test_tenant_b_reserved_share_not_eaten_by_a():
    limiter = StrongLimiter(inflight_limit=5, queue_max=0, reserved_share={"A": 0.0, "B": 0.4})

    async def run() -> None:
        # B reserved = max(1, round(0.4*5)) = 2. Shared = 3.
        for _ in range(3):
            got = await limiter.acquire("A")
            assert got.ok
        # A cannot take B's reserved 2 slots
        denied = await limiter.acquire("A")
        assert not denied.ok
        b1 = await limiter.acquire("B")
        b2 = await limiter.acquire("B")
        assert b1.ok and b2.ok
        b3 = await limiter.acquire("B")
        assert not b3.ok
        await limiter.release("A")
        await limiter.release("A")
        await limiter.release("A")
        await limiter.release("B")
        await limiter.release("B")

    asyncio.run(run())


def test_token_bucket_rejects_when_bg_exhausted():
    limiter = StrongLimiter(inflight_limit=8, queue_max=0, bg_rps=100.0, burst=1, overflow_mode="reject")

    async def run() -> None:
        first = await limiter.acquire("A")
        assert first.ok
        second = await limiter.acquire("A")
        assert not second.ok
        assert second.reason == "strong_full"
        await limiter.release("A")

    asyncio.run(run())


def test_sensitive_reserved_tokens_not_stolen_while_busy():
    limiter = StrongLimiter(
        inflight_limit=8,
        queue_max=0,
        reserved_share={"A": 0.0, "B": 0.5},
        bg_rps=100.0,
        burst=1,
        overflow_mode="reject",
    )

    async def run() -> None:
        a = await limiter.acquire("A")
        b = await limiter.acquire("B")
        assert a.ok and b.ok
        a2 = await limiter.acquire("A")
        assert not a2.ok
        b2 = await limiter.acquire("B")
        assert not b2.ok
        await limiter.release("A")
        await limiter.release("B")

    asyncio.run(run())


def test_idle_reserved_tokens_are_stealable():
    limiter = StrongLimiter(
        inflight_limit=8,
        queue_max=0,
        reserved_share={"A": 0.0, "B": 0.5},
        bg_rps=100.0,
        burst=1,
        overflow_mode="reject",
    )

    async def run() -> None:
        a = await limiter.acquire("A")
        assert a.ok
        stolen = await limiter.acquire("A")
        assert stolen.ok
        await limiter.release("A")
        await limiter.release("A")

    asyncio.run(run())


def test_present_tenant_reserved_not_stolen_after_idle_release():
    limiter = StrongLimiter(
        inflight_limit=8,
        queue_max=0,
        reserved_share={"A": 0.0, "B": 0.5},
        bg_rps=100.0,
        burst=1,
        overflow_mode="reject",
    )

    async def run() -> None:
        assert limiter.strong_available("B")
        a = await limiter.acquire("A")
        assert a.ok
        stolen = await limiter.acquire("A")
        assert not stolen.ok
        await limiter.release("A")

    asyncio.run(run())
