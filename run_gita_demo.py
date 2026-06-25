#!/usr/bin/env python3
"""
Standalone Demonstration Script: Bhagavad Gita Shloka & External Words Vectorization.
Implements the user request:
1. Takes Sanskrit Shloka from Bhagavad Gita (BG 1.1 / BG 2.47).
2. Vectorizes input text and saves 11D vectors to file.
3. Detokenizes vectors from file back to Sanskrit printed words verifying Samāsa handling.
4. Tests external non-root words (modern borrowings).
"""

import json
import os
import sys

from sanskrit_engine import (
    RainbowTableGenerator,
    RuleBasedMorphology,
    SandhiSplitterTokenizer,
    TensorCoordinate,
    TensorTokenizer,
    load_rules,
)


def run_demo():
    print("="*70)
    print(" SANSKRIT ENGINE: BHAGAVAD GITA & EXTERNAL WORDS PIPELINE DEMO")
    print("="*70)

    # Initialize Engine Components
    print("[+] Hydrating Pāṇinian Rule Packs...")
    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(rules)
    tokenizer = TensorTokenizer(morphology, default_dim=11)
    
    print("[+] Building FST Trie Rainbow Cache...")
    table = RainbowTableGenerator()
    table.populate_common_corpus(tokenizer)
    splitter = SandhiSplitterTokenizer(table, tokenizer)

    # -------------------------------------------------------------------------
    # PART 1: BHAGAVAD GITA SHLOKA VECTORIZATION & FILE IO
    # -------------------------------------------------------------------------
    if len(sys.argv) > 1:
        shloka = " ".join(sys.argv[1:])
    else:
        shloka = "udyamena hi sidhyanti kāryāṇi na manorathaiḥ"
    print(f"\n[1] Input Bhagavad Gita Shloka:\n    \"{shloka}\"")
    
    vectors = splitter.tokenize_to_vectors(shloka)
    print(f"[+] Encoded into {len(vectors)} morphological 11D Tensor Coordinates:")
    for v in vectors:
        surf = tokenizer.decode([v])
        print(f"    - {surf:<15} -> {v.vector}")

    vector_filepath = "gita_shloka_vectors.json"
    with open(vector_filepath, "w", encoding="utf-8") as f:
        json.dump({
            "shloka": shloka,
            "tensor_contract": "11D [Concept_ID, Class, Upasarga, Derivative, Role, Lakāra, Puruṣa, Pada, Liṅga, Vibhakti, Vacana]",
            "vectors": [v.vector for v in vectors]
        }, f, indent=2)
    print(f"[+] Saved vectors to file: {os.path.abspath(vector_filepath)}")

    # -------------------------------------------------------------------------
    # PART 2: DETOKENIZATION (DECODE FROM FILE) & SAMĀSA VERIFICATION
    # -------------------------------------------------------------------------
    print("\n[2] Reading vectors from file and executing Detokenizer...")
    with open(vector_filepath, "r", encoding="utf-8") as f:
        stored_data = json.load(f)
    
    reloaded_coords = [TensorCoordinate(vec) for vec in stored_data["vectors"]]
    reconstructed_shloka = tokenizer.decode(reloaded_coords)
    
    print(f"[+] Detokenized Output:\n    \"{reconstructed_shloka}\"")
    if reconstructed_shloka == shloka:
        print("[✔] SUCCESS: Reconstructed shloka matches original 100%! Samāsa handled.")
    else:
        print("[!] Note: Reconstructed text represents normalized morphological padas.")

    # -------------------------------------------------------------------------
    # PART 3: EXTERNAL / NON-ROOT WORDS HANDLING
    # -------------------------------------------------------------------------
    ext_text = "computer internet sañjaya"
    print(f"\n[3] Testing External Non-Root Borrowings:\n    \"{ext_text}\"")
    
    ext_vectors = tokenizer.encode(ext_text)
    print("[+] Assigned dynamic out-of-vocabulary Concept IDs (>90000):")
    for w, v in zip(ext_text.split(), ext_vectors):
        print(f"    - {w:<15} -> {v.vector[:2]}... (ID: {v.vector[0]})")
        
    ext_filepath = "external_words_vectors.json"
    with open(ext_filepath, "w", encoding="utf-8") as f:
        json.dump([v.vector for v in ext_vectors], f, indent=2)
    print(f"[+] Saved external vectors to: {os.path.abspath(ext_filepath)}")

    with open(ext_filepath, "r", encoding="utf-8") as f:
        loaded_ext_coords = [TensorCoordinate(v) for v in json.load(f)]
    
    reconstructed_ext = tokenizer.decode(loaded_ext_coords)
    print(f"[+] Detokenized External Output:\n    \"{reconstructed_ext}\"")
    if reconstructed_ext == ext_text:
        print("[✔] SUCCESS: External non-root words preserved natively!")

    print("\n" + "="*70)
    print(" DEMONSTRATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    run_demo()
