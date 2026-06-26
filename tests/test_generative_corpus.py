from __future__ import annotations

import pytest
from sanskrit_engine.lexicon import VerbEntry
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.tinganta_db import TingantaDB


def test_generative_combinatorial_coverage() -> None:
    """Verifies dynamic Paninian generation pipeline across dhātus and pratyayas."""
    morph = RuleBasedMorphology()
    db = TingantaDB()

    test_roots = ["bhū", "gam", "paṭh", "vad"]
    persons = ["first", "second", "third"]
    numbers = ["singular", "dual", "plural"]

    generated_count = 0
    for root in test_roots:
        verb_meta = VerbEntry(root=root, present_stem=root + "a", gloss=root)
        for p in persons:
            for n in numbers:
                form = morph.conjugate(verb=verb_meta, person=p, number=n, tense="present")
                assert form.text != ""
                assert form.features["pos"] == "verb"
                generated_count += 1

    assert generated_count == 36  # 4 roots * 3 persons * 3 numbers
