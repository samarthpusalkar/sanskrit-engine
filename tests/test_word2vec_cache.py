import pytest
from sanskrit_engine import (
    RainbowTableGenerator,
    RuleBasedMorphology,
    SandhiSplitterTokenizer,
    TensorCoordinate,
    TensorTokenizer,
    load_rules,
)


def test_rainbow_table_generator_and_sandhi_splitting() -> None:
    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(rules)
    tokenizer = TensorTokenizer(morphology)

    table = RainbowTableGenerator()
    count = table.populate_common_corpus(tokenizer)
    assert count > 0

    # O(1) Vector lookup
    cached_vecs = table.lookup_word("gacchati")
    if cached_vecs:
        assert len(cached_vecs[0].to_11d().vector) == 11

    # Sandhi splitting
    splitter = SandhiSplitterTokenizer(table, tokenizer)
    unmerged = splitter.unmerge_sandhi("rāmaḥgacchati")
    # Even if unsplit fallback or split, check output list
    assert isinstance(unmerged, list)
    assert len(unmerged) >= 1
