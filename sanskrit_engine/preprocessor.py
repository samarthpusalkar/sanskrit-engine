from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def hydrate_rule_config(data: dict[str, Any] | list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Flatten inherited rule fields into executable rule records.

    Supported inheritance:
    - `inherits`: rule id or list of rule ids
    - parent fields merge into child fields
    - child values override parent values
    - nested dicts merge recursively
    """

    records = _records(data)
    by_id = {str(record["id"]): record for record in records}
    hydrated: dict[str, dict[str, Any]] = {}

    def resolve(rule_id: str, stack: tuple[str, ...] = ()) -> dict[str, Any]:
        if rule_id in hydrated:
            return copy.deepcopy(hydrated[rule_id])
        if rule_id in stack:
            raise ValueError(f"Cyclic rule inheritance: {' -> '.join(stack + (rule_id,))}")
        record = by_id[rule_id]
        parents = record.get("inherits", [])
        if isinstance(parents, str):
            parents = [parents]

        merged: dict[str, Any] = {}
        for parent_id in parents:
            if parent_id not in by_id:
                raise KeyError(f"Unknown inherited rule id: {parent_id}")
            merged = _deep_merge(merged, resolve(parent_id, stack + (rule_id,)))

        child = copy.deepcopy(record)
        child.pop("inherits", None)
        merged = _deep_merge(merged, child)
        hydrated[rule_id] = merged
        return copy.deepcopy(merged)

    return {"rules": [resolve(str(record["id"])) for record in records]}


def hydrate_rule_file(input_path: str | Path, output_path: str | Path) -> None:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    hydrated = hydrate_rule_config(data)
    Path(output_path).write_text(
        json.dumps(hydrated, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _records(data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    for key in ("rules", "data", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    raise ValueError("Rule config must be list or object with rules/data/items list")


def _deep_merge(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(parent)
    for key, value in child.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result

