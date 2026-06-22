from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import generate_jsonl
from .enforcer import RuleEnforcer
from .loader import load_rules
from .generator import SanskritGenerator
from .morphology import RuleBasedMorphology
from .parser import SanskritParser
from .sutra import export_rule_stubs, load_sutras


def main() -> None:
    parser = argparse.ArgumentParser(prog="sanskrit-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stubs = subparsers.add_parser("export-stubs")
    stubs.add_argument("sutra_path", help="Path to ashtadhyayi-data/sutraani/data.txt")
    stubs.add_argument("output_path", help="Where to write normalized rule stubs JSON")

    dataset = subparsers.add_parser("generate-jsonl")
    dataset.add_argument("output_path", help="Where to write JSONL dataset")
    dataset.add_argument("--count", type=int, default=100)
    dataset.add_argument("--rules", default=None, help="Optional executable rule JSON")
    dataset.add_argument(
        "--morphology-rules",
        default=None,
        help="Comma-separated rule JSON files for generating forms by derivation",
    )
    dataset.add_argument("--sandhi", action="store_true", help="Apply bundled v0 sandhi rule pack")
    dataset.add_argument("--seed", type=int, default=0)

    parse = subparsers.add_parser("parse")
    parse.add_argument("text", help="Sanskrit text to parse")

    inspect = subparsers.add_parser("inspect-rules")
    inspect.add_argument("rule_path", help="Executable rule JSON or exported stubs JSON")

    args = parser.parse_args()
    if args.command == "export-stubs":
        sutras = load_sutras(args.sutra_path)
        output = export_rule_stubs(sutras)
        Path(args.output_path).write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif args.command == "generate-jsonl":
        rules_path = args.rules
        if args.sandhi and rules_path is None:
            rules_path = str(Path(__file__).resolve().parents[1] / "data" / "rules" / "sandhi.json")
        enforcer = RuleEnforcer(load_rules(rules_path)) if rules_path else None
        morphology = None
        if args.morphology_rules:
            morph_rules = []
            for path in args.morphology_rules.split(","):
                morph_rules.extend(load_rules(path))
            morphology = RuleBasedMorphology(morph_rules)
        generate_jsonl(
            args.output_path,
            count=args.count,
            generator=SanskritGenerator(seed=args.seed, morphology=morphology),
            enforcer=enforcer,
        )
    elif args.command == "parse":
        result = SanskritParser().parse(args.text)
        print(
            json.dumps(
                {
                    "input_text": result.input_text,
                    "phonemes": [
                        {"value": token.value, "index": token.index, "kind": token.kind}
                        for token in result.phonemes
                    ],
                    "nodes": [
                        {"text": node.text, "kind": node.kind, "features": node.features}
                        for node in result.nodes
                    ],
                    "sandhi_candidates": [
                        {
                            "left": split.left,
                            "right": split.right,
                            "rule_id": split.rule_id,
                            "confidence": split.confidence,
                        }
                        for split in result.sandhi_candidates
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "inspect-rules":
        data = json.loads(Path(args.rule_path).read_text(encoding="utf-8"))
        records = data["rules"] if isinstance(data, dict) and "rules" in data else data
        executable = [
            record
            for record in records
            if record.get("operation", {}).get("type") not in {None, "noop"}
        ]
        print(
            json.dumps(
                {
                    "total": len(records),
                    "executable": len(executable),
                    "stubs": len(records) - len(executable),
                    "types": _count_by(records, "type"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def _count_by(records: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


if __name__ == "__main__":
    main()
