import json
import subprocess
import sys

from sanskrit_engine import (
    Engine,
    Rule,
    SanskritGenerator,
    SanskritParser,
    Token,
    export_rule_stubs,
    load_rules,
    load_sutras,
)
from sanskrit_engine.dataset import generate_jsonl
from sanskrit_engine.enforcer import RuleEnforcer
from sanskrit_engine.lexicon import NounEntry, VerbEntry
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.pratyahara import PratyaharaResolver


def test_sample_rules_merge_vowels_and_delete_it() -> None:
    rules = load_rules("data/sample_rules.json")
    result = Engine(rules).process([Token("a"), Token("a"), Token("x", {"it"})])

    assert result.text == "ā"
    assert result.halted_reason == "stable"
    assert [step.rule_id for step in result.trace] == [
        "6.1.sample.dirgha",
        "1.3.sample.it-delete",
    ]


def test_right_operand_wins_conflict_when_priority_equal() -> None:
    left_rule = Rule.from_dict(
        {
            "id": "left",
            "name": "left operand candidate",
            "type": "vidhi",
            "priority": 0,
            "scope": "left_operand",
            "conditions": {"target": {"text": "x"}},
            "operation": {"type": "replace_text", "text": "L"},
        },
        source_order=10,
    )
    right_rule = Rule.from_dict(
        {
            "id": "right",
            "name": "right operand candidate",
            "type": "vidhi",
            "priority": 0,
            "scope": "right_operand",
            "conditions": {"target": {"text": "x"}},
            "operation": {"type": "replace_text", "text": "R"},
        },
        source_order=1,
    )

    result = Engine([left_rule, right_rule]).process([Token("x")])

    assert result.text == "R"
    assert result.trace[0].rule_id == "right"


def test_cycle_detected() -> None:
    rules = [
        Rule.from_dict(
            {
                "id": "a-to-b",
                "name": "a to b",
                "type": "vidhi",
                "priority": 0,
                "conditions": {"target": {"text": "a"}},
                "operation": {"type": "replace_text", "text": "b"},
            },
            source_order=0,
        ),
        Rule.from_dict(
            {
                "id": "b-to-a",
                "name": "b to a",
                "type": "vidhi",
                "priority": 0,
                "conditions": {"target": {"text": "b"}},
                "operation": {"type": "replace_text", "text": "a"},
            },
            source_order=1,
        ),
    ]

    result = Engine(rules).process([Token("a")])

    assert result.halted_reason == "cycle_detected"


def test_pratyahara_resolver_from_mapping() -> None:
    resolver = PratyaharaResolver.from_mapping({"अच्": ["अ", "इ"]})

    assert resolver.contains("अच्", "अ")
    assert not resolver.contains("अच्", "क्")


def test_sutra_importer_and_stub_export(tmp_path) -> None:
    path = tmp_path / "sutraani.json"
    path.write_text(
        """
        {
          "name": "sutraani",
          "data": [
            {
              "i": "11001",
              "a": "1",
              "p": "1",
              "n": "1",
              "s": "वृद्धिरादैच्",
              "type": "S$वृद्धिसंज्ञा$",
              "pc": "वृद्धिः$S$1$1$##आत्-ऐच्$S$1$1$",
              "an": ""
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    sutras = load_sutras(path)
    stubs = export_rule_stubs(sutras)

    assert sutras[0].rule_id == "1.1.1"
    assert stubs["rules"][0]["type"] == "samjna"
    assert stubs["rules"][0]["operation"] == {"type": "noop"}


def test_parser_returns_phonemes_nodes_and_sandhi_candidates() -> None:
    result = SanskritParser().parse("rāmaḥ gacchati")

    assert result.nodes[0].kind == "noun"
    assert result.nodes[1].kind == "verb"
    assert any(token.value == "ā" for token in result.phonemes)
    assert result.sandhi_candidates


def test_generator_creates_traceable_sentence() -> None:
    sentence = SanskritGenerator(seed=1).generate_many(1)[0]

    assert sentence.text
    assert sentence.forms
    assert sentence.rule_ids


def test_generate_jsonl_writes_training_records(tmp_path) -> None:
    path = tmp_path / "synthetic.jsonl"

    generate_jsonl(path, count=3, generator=SanskritGenerator(seed=2))

    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    assert len(rows) == 3
    assert rows[0]["id"] == "synthetic-00000000"
    assert rows[0]["text"]
    assert rows[0]["forms"]


def test_rule_enforcer_preserves_word_spacing() -> None:
    rules = load_rules("data/sample_rules.json")
    result = RuleEnforcer(rules).enforce_text("rāmaḥ gacchati")

    assert result.output_text == "rāmaḥ gacchati"
    assert result.ok


def test_sandhi_rule_pack_rewrites_word_boundaries() -> None:
    enforcer = RuleEnforcer(load_rules("data/rules/sandhi.json"))

    assert enforcer.enforce_text("rāmaḥ asti").output_text == "rāmo 'sti"
    assert enforcer.enforce_text("deva avatāraḥ").output_text == "devāvatāraḥ"
    assert enforcer.enforce_text("rāmaḥ gacchati").output_text == "rāmo gacchati"


def test_cli_parse_and_inspect_rules() -> None:
    parsed = subprocess.run(
        [sys.executable, "-m", "sanskrit_engine.cli", "parse", "rāmaḥ gacchati"],
        check=True,
        capture_output=True,
        text=True,
    )
    parse_data = json.loads(parsed.stdout)

    inspected = subprocess.run(
        [sys.executable, "-m", "sanskrit_engine.cli", "inspect-rules", "data/rules/sandhi.json"],
        check=True,
        capture_output=True,
        text=True,
    )
    inspect_data = json.loads(inspected.stdout)

    assert parse_data["nodes"][0]["kind"] == "noun"
    assert inspect_data["executable"] >= 1


def test_rule_based_morphology_derives_forms() -> None:
    morphology = RuleBasedMorphology(
        load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    )

    rāma = NounEntry("rāma", "masculine", "Rama")
    phala = NounEntry("phala", "neuter", "fruit")
    gam = VerbEntry("gam", "gaccha", "go")

    assert morphology.decline(rāma, "nominative", "singular").text == "rāmaḥ"
    assert morphology.decline(rāma, "accusative", "singular").text == "rāmam"
    assert morphology.decline(phala, "nominative", "plural").text == "phalāni"
    assert morphology.conjugate(gam, "third", "singular", "present").text == "gacchati"


def test_cli_generates_jsonl_with_morphology_and_sandhi(tmp_path) -> None:
    path = tmp_path / "out.jsonl"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sanskrit_engine.cli",
            "generate-jsonl",
            str(path),
            "--count",
            "2",
            "--seed",
            "0",
            "--morphology-rules",
            "data/rules/subanta.json,data/rules/tinanta.json",
            "--sandhi",
        ],
        check=True,
    )

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["forms"][0]["rule_ids"]
    assert rows[0]["enforcement"]["ok"]
