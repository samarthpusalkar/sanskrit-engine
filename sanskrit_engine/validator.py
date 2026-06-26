from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .enforcer import RuleEnforcer
from .lexicon import NounEntry, VerbEntry
from .loader import load_rules
from .morphology import GenerativePaniniMorphology


@dataclass(frozen=True)
class ValidationCaseResult:
    id: str
    ok: bool
    expected: str
    actual: str
    rule_ids: tuple[str, ...]
    message: str = ""


@dataclass(frozen=True)
class ValidationReport:
    total: int
    passed: int
    failed: int
    cases: tuple[ValidationCaseResult, ...]

    @property
    def ok(self) -> bool:
        return self.failed == 0


def validate_fixture(path: str | Path) -> ValidationReport:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = raw["cases"] if isinstance(raw, dict) and "cases" in raw else raw
    results = tuple(_validate_case(case) for case in cases)
    passed = sum(result.ok for result in results)
    return ValidationReport(
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        cases=results,
    )


def report_to_dict(report: ValidationReport) -> dict[str, Any]:
    return {
        "ok": report.ok,
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "cases": [
            {
                "id": case.id,
                "ok": case.ok,
                "expected": case.expected,
                "actual": case.actual,
                "rule_ids": list(case.rule_ids),
                "message": case.message,
            }
            for case in report.cases
        ],
    }


def _validate_case(case: dict[str, Any]) -> ValidationCaseResult:
    try:
        actual, rule_ids = _derive(case)
        expected = str(case["expected"])
        return ValidationCaseResult(
            id=str(case["id"]),
            ok=actual == expected,
            expected=expected,
            actual=actual,
            rule_ids=rule_ids,
            message="" if actual == expected else "output mismatch",
        )
    except Exception as exc:
        return ValidationCaseResult(
            id=str(case.get("id", "unknown")),
            ok=False,
            expected=str(case.get("expected", "")),
            actual="",
            rule_ids=(),
            message=f"{type(exc).__name__}: {exc}",
        )


def _derive(case: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    rules = []
    for path in case["rules"]:
        rules.extend(load_rules(path))

    kind = case["kind"]
    if kind == "sandhi":
        result = RuleEnforcer(rules).enforce_text(" ".join(case["input"]))
        return result.output_text, tuple(step.rule_id for step in result.engine_result.trace)

    morphology = GenerativePaniniMorphology(rules)
    if kind == "noun":
        form = morphology.decline(
            NounEntry(str(case["lemma"]), str(case["gender"]), str(case.get("gloss", ""))),
            str(case["case"]),
            str(case["number"]),
        )
        return form.text, form.rule_ids

    if kind == "verb":
        form = morphology.conjugate(
            VerbEntry(str(case["root"]), str(case["present_stem"]), str(case.get("gloss", ""))),
            str(case["person"]),
            str(case["number"]),
            str(case["tense"]),
        )
        return form.text, form.rule_ids

    raise ValueError(f"Unsupported validation kind: {kind}")

