from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .rules import Rule


def load_rules(path: str | Path) -> list[Rule]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = _extract_records(data)
    return [Rule.from_dict(record, source_order=i) for i, record in enumerate(records)]


def _extract_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("rules", "data", "items"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    raise ValueError("Rule file must be list or object with rules/data/items list")

