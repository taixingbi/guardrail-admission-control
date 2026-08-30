#!/usr/bin/env python3
"""Fine-tune MiniLM on WildGuard *train* only. P4 freeze is never in the train set."""

from __future__ import annotations

import json
import random
from pathlib import Path

from gasc.g_light import DEFAULT_BASE, DEFAULT_MODEL_DIR
from gasc.paths import repo_root


def _load_train(path: Path) -> list[tuple[str, int]]:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        text = rec.get("prompt") or rec.get("text")
        gt = rec.get("gt") or rec.get("prompt_harm_label")
        if not text:
            continue
        if gt in {"unsafe", "harmful"}:
            rows.append((text, 1))
        elif gt in {"safe", "unharmful"}:
            rows.append((text, 0))
    return rows


def main() -> int:
    root = repo_root()
    train_path = root / "data" / "external" / "wildguardtrain.jsonl"
    if not train_path.exists():
        raise SystemExit("missing data/external/wildguardtrain.jsonl — run scripts/fetch_wildguard_train.py")
    rows = _load_train(train_path)
    rng = random.Random(7)
    rng.shuffle(rows)
    # Cap so a laptop can finish; full train is optional via env.
    import os

    cap = int(os.environ.get("GASC_GLIGHT_TRAIN_CAP", "12000"))
    if cap > 0 and len(rows) > cap:
        pos = [r for r in rows if r[1] == 1][: cap // 2]
        neg = [r for r in rows if r[1] == 0][: cap // 2]
        rows = pos + neg
        rng.shuffle(rows)
    n_val = max(200, int(0.1 * len(rows)))
    val, train = rows[:n_val], rows[n_val:]
    print(f"train={len(train)} val={len(val)} pos={sum(y for _, y in train)}", flush=True)

    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    class _DS(Dataset):
        def __init__(self, pairs, tok):
            self.pairs = pairs
            self.tok = tok

        def __len__(self):
            return len(self.pairs)

        def __getitem__(self, i):
            text, y = self.pairs[i]
            enc = self.tok(text, truncation=True, max_length=256, padding="max_length", return_tensors="pt")
            item = {k: v.squeeze(0) for k, v in enc.items()}
            item["labels"] = torch.tensor(y)
            return item

    tok = AutoTokenizer.from_pretrained(DEFAULT_BASE)
    model = AutoModelForSequenceClassification.from_pretrained(DEFAULT_BASE, num_labels=2)
    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
    model.to(device)
    epochs = int(os.environ.get("GASC_GLIGHT_EPOCHS", "2"))
    bs = int(os.environ.get("GASC_GLIGHT_BS", "16"))
    train_loader = DataLoader(_DS(train, tok), batch_size=bs, shuffle=True)
    val_loader = DataLoader(_DS(val, tok), batch_size=bs)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5)
    steps = max(1, epochs * len(train_loader))
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)

    def _acc(loader) -> float:
        model.eval()
        ok = n = 0
        with torch.no_grad():
            for batch in loader:
                labels = batch.pop("labels").to(device)
                batch = {k: v.to(device) for k, v in batch.items()}
                pred = model(**batch).logits.argmax(dim=-1)
                ok += int((pred == labels).sum().item())
                n += len(labels)
        return ok / max(n, 1)

    for epoch in range(1, epochs + 1):
        model.train()
        total = 0.0
        for i, batch in enumerate(train_loader, start=1):
            labels = batch.pop("labels").to(device)
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(**batch, labels=labels)
            out.loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
            total += float(out.loss.item())
            if i % 50 == 0:
                print(f"epoch {epoch} step {i}/{len(train_loader)} loss={total / i:.4f}", flush=True)
        print(f"epoch {epoch} val_acc={_acc(val_loader):.3f}", flush=True)

    out = DEFAULT_MODEL_DIR
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    (out / "train_meta.json").write_text(
        json.dumps(
            {
                "base": DEFAULT_BASE,
                "n_train": len(train),
                "n_val": len(val),
                "source": "wildguardmix_train",
                "held_out": "P4 freeze + WildGuardTest + XSTest",
            },
            indent=2,
        )
    )
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
