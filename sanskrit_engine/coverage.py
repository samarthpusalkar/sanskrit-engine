from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SUTRA_ID_RE = re.compile(r"^(\d+\.\d+\.\d+)")


def rule_coverage(stub_path: str | Path, rule_paths: list[str | Path]) -> dict[str, Any]:
    stubs = _records(stub_path)
    executable = []
    for path in rule_paths:
        executable.extend(_records(path))

    source_ids = {str(record["id"]) for record in stubs}
    executable_ids = {
        sutra_prefix(str(record["id"]))
        for record in executable
        if record.get("operation", {}).get("type") not in {None, "noop"}
    }
    executable_ids.discard("")
    covered = source_ids & executable_ids
    return {
        "source_total": len(source_ids),
        "rule_total": len(executable),
        "executable_total": len(executable_ids),
        "covered_source_ids": len(covered),
        "coverage_ratio": (len(covered) / len(source_ids)) if source_ids else 0.0,
        "covered": sorted(covered),
        "encoded_without_source_match": sorted(executable_ids - source_ids),
    }


def sutra_prefix(rule_id: str) -> str:
    match = SUTRA_ID_RE.match(rule_id)
    return match.group(1) if match else ""


def _records(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    for key in ("rules", "data", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    raise ValueError(f"Unsupported JSON record shape: {path}")

