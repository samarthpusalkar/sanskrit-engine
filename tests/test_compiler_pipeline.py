import pytest
from sanskrit_engine.pratyahara import PratyaharaResolver
from sanskrit_engine.panini_parser import CaseCompiler
from sanskrit_engine.compiler_pipeline import (
    DerivationContext,
    GamToGacchRule,
    GrammarEngine,
    HanToGhnRule,
    PaniniRule,
    RuleFactory,
    SamjnaRule,
)


def test_derivation_context_vector_parsing() -> None:
    vec_dict = {
        "concept_id": 101,
        "word_class": 1,
        "lakara": 1,
        "purusa": 1,
        "pada": 1,
        "vacana": 3,
    }
    ctx = DerivationContext(vec_dict, "gam")
    assert ctx.pos == "verb"
    assert ctx.person == "third"
    assert ctx.number == "plural"
    assert ctx.stem == "gam"


def test_grammar_engine_gam_derivation() -> None:
    engine = GrammarEngine()
    # gam + third singular present -> gacch + a + ti -> gacchati
    res = engine.generate([101, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1], {"gana": "1", "pada": "P"}, "gam")
    assert res == "gacchati"


def test_grammar_engine_han_apavada() -> None:
    engine = GrammarEngine()
    # han + third plural present -> ghn + nti -> ghnanti
    res = engine.generate([102, 1, 0, 0, 0, 1, 1, 1, 1, 1, 3], {"gana": "2", "pada": "P"}, "han")
    assert res == "ghnanti"


def test_rule_factory() -> None:
    cfg = {
        "rule_id": "9.9.9",
        "name": "test rule",
        "category": "anga_karya",
        "operation": {"executable": "lambda tok, env: {'text': tok['text'] + 'X'}"},
    }
    rule = RuleFactory.create_rule(cfg)
    ctx = DerivationContext([0]*11, "test")
    rule.apply(ctx)
    assert ctx.stem == "testX"


def test_pratyahara_unzipper_shiva_sutras() -> None:
    resolver = PratyaharaResolver()
    assert resolver.decode("ik") == ["i", "u", "ṛ", "ḷ"]
    assert resolver.decode("yaṇ") == ["y", "v", "r", "l"]
    assert resolver.decode("ac") == ["a", "i", "u", "ṛ", "ḷ", "e", "o", "ai", "au"]


def test_case_compiler_vibhakti_resolution() -> None:
    compiler = CaseCompiler()
    padaccheda = [
        {"pada": "इकः", "pada_split": "ik", "vibhakti": 6},
        {"pada": "यण्", "pada_split": "yaṇ", "vibhakti": 1},
        {"pada": "अचि", "pada_split": "ac", "vibhakti": 7},
    ]
    ir = compiler.compile_rule_to_ir("6.1.77", padaccheda, ["विधि"], "sandhi")
    assert ir["conditions"]["target_regex"] == "[i, u, ṛ, ḷ]"
    assert ir["conditions"]["lookahead_regex"] == "[a, i, u, ṛ, ḷ, e, o, ai, au]"
    assert ir["operations"]["substitute"] == ["y", "v", "r", "l"]


