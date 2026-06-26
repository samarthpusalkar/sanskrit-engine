from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SutraRecord:
    id: str
    adhyaya: int
    pada: int
    number: int
    text: str
    type_code: str = ""
    padaccheda: str = ""
    anuvritti: tuple[str, ...] = ()
    source_order: int = 0

    @property
    def rule_id(self) -> str:
        return f"{self.adhyaya}.{self.pada}.{self.number}"


def load_sutras(path: str | Path) -> list[SutraRecord]:
    """Load `ashtadhyayi-data/sutraani/data.txt` or `ska/data.txt`."""

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    records = raw["data"] if isinstance(raw, dict) and "data" in raw else raw
    return [_record_from_dict(record, i) for i, record in enumerate(records)]


def export_rule_stubs(sutras: list[SutraRecord]) -> dict[str, list[dict[str, Any]]]:
    """Create fillable executable-rule stubs from source sutras.

    Human/LLM annotator fills `conditions` and `operation` later.
    """

    return {
        "rules": [
            {
                "id": sutra.rule_id,
                "source_id": sutra.id,
                "name": sutra.text,
                "sutra_text": sutra.text,
                "type": _type_from_code(sutra.type_code),
                "priority": sutra.source_order,
                "conditions": {},
                "operation": {"type": "noop"},
                "symbolic_rule_spec": {
                    "left_context": None,
                    "right_context": None,
                    "target_context": None,
                    "operation": {"op_kind": "substitute", "target_scope": "target"},
                },
                "metadata": {
                    "padaccheda": sutra.padaccheda,
                    "anuvritti": list(sutra.anuvritti),
                    "type_code": sutra.type_code,
                },
            }
            for sutra in sutras
        ]
    }


def _record_from_dict(record: dict[str, Any], source_order: int) -> SutraRecord:
    anuvritti = tuple(
        item
        for item in str(record.get("an", "")).split("##")
        if item
    )
    return SutraRecord(
        id=str(record.get("i") or record.get("ind") or source_order),
        adhyaya=int(record["a"]),
        pada=int(record["p"]),
        number=int(record["n"]),
        text=str(record["s"]),
        type_code=str(record.get("type", "")),
        padaccheda=str(record.get("pc", "")),
        anuvritti=anuvritti,
        source_order=source_order,
    )


def _type_from_code(type_code: str) -> str:
    if type_code.startswith("P$"):
        return "paribhasha"
    if type_code.startswith("A$"):
        return "adhikara"
    if "संज्ञा" in type_code:
        return "samjna"
    return "vidhi"

