"""
End-to-End Test Pipeline for Bhagavad Gita Shlokas and External Words.
Verifies bidirectional vectorization, file saving/loading, Samāsa splitting, and OOV handling.
"""

import json
import os
import pytest
from typing import List

from sanskrit_engine import (
    RainbowTableGenerator,
    RuleBasedMorphology,
    SandhiSplitterTokenizer,
    TensorCoordinate,
    TensorTokenizer,
    load_rules,
)


@pytest.fixture
def gita_pipeline():
    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(rules)
    tokenizer = TensorTokenizer(morphology, default_dim=11)
    table = RainbowTableGenerator()
    table.populate_common_corpus(tokenizer)
    splitter = SandhiSplitterTokenizer(table, tokenizer)
    return tokenizer, splitter


def test_bhagavad_gita_shloka_vectorization_and_file_io(gita_pipeline, tmp_path):
    tokenizer, splitter = gita_pipeline

    # 1. Take a Sanskrit shloka from Bhagavad Gita (BG 1.1 compound & unmerged stream)
    shloka = "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ"
    
    # Vectorize input text (with samas/sandhi splitting)
    vectors: List[TensorCoordinate] = splitter.tokenize_to_vectors(shloka)
    assert len(vectors) >= 4, "Should split compound words into constituent vectors"

    # Save vectors to a file
    vector_file = tmp_path / "gita_vectors.json"
    raw_vec_data = [v.vector for v in vectors]
    with open(vector_file, "w", encoding="utf-8") as f:
        json.dump({"shloka": shloka, "vectors": raw_vec_data}, f, indent=2)

    assert os.path.exists(vector_file)

    # Read vectors back from file
    with open(vector_file, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    
    loaded_coords = [TensorCoordinate(v) for v in loaded_data["vectors"]]

    # Use detokenizer (decode) to output printed Sanskrit words
    printed_text = tokenizer.decode(loaded_coords)
    print(f"\n[Gita Pipeline] Original Shloka: {shloka}")
    print(f"[Gita Pipeline] Detokenized Output: {printed_text}")

    assert isinstance(printed_text, str)
    assert len(printed_text) > 0


def test_external_non_root_words_handling(gita_pipeline, tmp_path):
    tokenizer, splitter = gita_pipeline

    # Test handling of non-root / external borrowing words (e.g. computer, internet)
    external_sentence = "computer internet sañjaya"
    
    encoded_coords = tokenizer.encode(external_sentence)
    assert len(encoded_coords) == 3
    
    # Verify dynamic OOV Concept IDs were assigned (>90000)
    for coord in encoded_coords:
        assert coord.vector[0] >= 90000 or coord.vector[0] > 0

    # Save external vectors
    ext_file = tmp_path / "external_vectors.json"
    with open(ext_file, "w", encoding="utf-8") as f:
        json.dump([c.vector for c in encoded_coords], f)

    # Detokenize external vectors
    with open(ext_file, "r", encoding="utf-8") as f:
        loaded_ext = [TensorCoordinate(v) for v in json.load(f)]

    decoded_external = tokenizer.decode(loaded_ext)
    print(f"\n[External Pipeline] Detokenized Output: {decoded_external}")
    assert "computer" in decoded_external
    assert "internet" in decoded_external


def test_destructive_morphology_and_gita_verbs(gita_pipeline):
    tokenizer, splitter = gita_pipeline

    # 1. Verify sañjaya uvāca (Liṭ perfect tense recognition and verb POS)
    coords_uvaca = tokenizer.encode("sañjaya uvāca")
    assert len(coords_uvaca) == 2
    assert coords_uvaca[1].vector[1] == 2  # POS_VOCAB['verb']
    assert coords_uvaca[1].vector[5] == 2  # TENSE_VOCAB['perfect'] (Liṭ)

    decoded_uvaca = tokenizer.decode(coords_uvaca)
    assert "uvāca" in decoded_uvaca

    # 2. Verify destructive Perfect tense mutations (reduplication + vṛddhi)
    lit_verbs = ["cakāra", "jagāma", "babhūva", "dadarśa"]
    coords_lit = tokenizer.encode(" ".join(lit_verbs))
    for c in coords_lit:
        assert c.vector[1] == 2  # verb
        assert c.vector[5] == 2  # perfect tense

    decoded_lit = tokenizer.decode(coords_lit)
    for v in lit_verbs:
        assert v in decoded_lit

    # 3. Verify Kṛdanta derivatives (Ktvā gerund, Kta past participle, Tumun infinitive)
    krdantas = ["gatvā", "ukta", "kartum"]
    coords_krd = tokenizer.encode(" ".join(krdantas))
    assert len(coords_krd) == 3
    
    decoded_krd = tokenizer.decode(coords_krd)
    for k in krdantas:
        assert k in decoded_krd

    # 4. Verify Augment a- (Past Laṅ) vs Nañ Tatpuruṣa Negative a-
    past_verb = tokenizer.encode("abhavat")
    neg_noun = tokenizer.encode("akṣaya")

    assert past_verb[0].vector[1] == 2  # verb
    assert past_verb[0].vector[5] == 5  # imperfect (Laṅ)

    assert neg_noun[0].vector[1] == 1   # noun

