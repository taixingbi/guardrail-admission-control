from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def write_jsonl(path: Path, rows: Iterable[BaseModel | dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            payload = row.model_dump_json() if isinstance(row, BaseModel) else json.dumps(row)
            fh.write(payload + "\n")


def load_jsonl(path: Path, model: type[T]) -> list[T]:
    rows: list[T] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(model.model_validate_json(line))
    return rows
