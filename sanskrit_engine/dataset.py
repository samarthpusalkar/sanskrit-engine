from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .enforcer import RuleEnforcer
from .generator import SanskritGenerator


def generate_jsonl(path: str | Path, count: int, generator: SanskritGenerator | None = None, enforcer: RuleEnforcer | None = None) -> None:
    generator = generator or SanskritGenerator()
    records = []
    for index, sentence in enumerate(generator.generate_many(count)):
        enforced = enforcer.enforce_text(sentence.text) if enforcer is not None else None
        records.append(
            {
                "id": f"synthetic-{index:08d}",
                "text": enforced.output_text if enforced else sentence.text,
                "raw_text": sentence.text,
                "gloss": sentence.gloss,
                "forms": [asdict(form) for form in sentence.forms],
                "rule_ids": list(sentence.rule_ids),
                "enforcement": {
                    "ok": enforced.ok,
                    "halted_reason": enforced.engine_result.halted_reason,
                    "trace": [
                        {
                            "rule_id": step.rule_id,
                            "rule_name": step.rule_name,
                            "index": step.index,
                        }
                        for step in enforced.engine_result.trace
                    ],
                    "issues": [asdict(issue) for issue in enforced.issues],
                }
                if enforced
                else None,
            }
        )

    with Path(path).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

