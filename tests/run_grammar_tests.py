#!/usr/bin/env python3
"""
Sanskrit Engine — Grammar Test Runner
======================================
Loads a JSON test-set (default: basic_grammar_tests.json), initialises the
full engine pipeline (Morphology → TensorTokenizer → RainbowTable → SandhiSplitter),
and for every test case:

  1. Tokenizes the input string to 11-D vectors via splitter.tokenize_to_vectors()
  2. Decodes the vectors back to text via tokenizer.decode()
  3. Compares the reconstructed text against the expected decoded tokens
  4. Logs per-case diagnostics and scores
  5. Writes aggregate metrics (overall, per-difficulty, per-category)

Results are printed to stdout AND saved to a CSV + summary text file so the
test-set JSON can be swapped without touching this script.

Usage
-----
    python tests/run_grammar_tests.py                       # default test-set
    python tests/run_grammar_tests.py path/to/other.json    # custom test-set
    python tests/run_grammar_tests.py --out-dir results/    # custom output dir
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so `sanskrit_engine` is importable
# when running this file directly (python tests/run_grammar_tests.py).
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sanskrit_engine import (
    GenerativePaniniMorphology,
    RainbowTableGenerator,
    SandhiSplitterTokenizer,
    TensorCoordinate,
    TensorTokenizer,
    load_rules,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _similarity_ratio(a: str, b: str) -> float:
    """Character-level similarity between two strings (0.0 – 1.0)."""
    return SequenceMatcher(None, a, b).ratio()


def _token_f1(predicted: List[str], expected: List[str]) -> Dict[str, float]:
    """
    Token-level precision / recall / F1 treating each list as a bag-of-tokens.
    Returns dict with keys: precision, recall, f1.
    """
    pred_set = set(predicted)
    exp_set = set(expected)
    if not pred_set and not exp_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = len(pred_set & exp_set)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(exp_set) if exp_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _exact_match(predicted: str, expected: str) -> bool:
    return predicted.strip() == expected.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Engine initialisation (mirrors run_gita_demo.py)
# ═══════════════════════════════════════════════════════════════════════════

def init_engine(rules_path: str = "data/rules/panini_ir_grammar.json"):
    """
    Bootstraps the full engine pipeline and returns (splitter, tokenizer).
    Identical initialisation sequence to run_gita_demo.py.
    """
    print("┌─────────────────────────────────────────────────────────┐")
    print("│  Initialising Sanskrit Engine Pipeline                  │")
    print("└─────────────────────────────────────────────────────────┘")

    t0 = time.perf_counter()
    print("[1/4] Hydrating Pāṇinian rule packs …")
    rules = load_rules(rules_path)
    morphology = GenerativePaniniMorphology(rules)
    tokenizer = TensorTokenizer(morphology, default_dim=11)

    print("[2/4] Building FST Trie Rainbow Cache …")
    table = RainbowTableGenerator()
    table.populate_common_corpus(tokenizer)

    print("[3/4] Constructing Sandhi Splitter Tokenizer …")
    splitter = SandhiSplitterTokenizer(table, tokenizer)

    elapsed = time.perf_counter() - t0
    print(f"[4/4] Engine ready  ({elapsed:.2f}s)\n")
    return splitter, tokenizer


# ═══════════════════════════════════════════════════════════════════════════
# Single test-case execution
# ═══════════════════════════════════════════════════════════════════════════

def run_single_test(
    tc: Dict[str, Any],
    splitter: SandhiSplitterTokenizer,
    tokenizer: TensorTokenizer,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Runs the encode → decode roundtrip for one test case dict and returns
    a result dict with all diagnostics.
    """
    tc_id = tc["id"]
    difficulty = tc.get("difficulty", "unknown")
    category = tc.get("category", "unknown")
    description = tc.get("description", "")
    input_string = tc["input_string"]
    expected_tokens = tc.get("expected_tokens", [])
    expected_text = " ".join(expected_tokens)

    result: Dict[str, Any] = {
        "id": tc_id,
        "difficulty": difficulty,
        "category": category,
        "input": input_string,
        "expected_tokens": expected_tokens,
        "expected_text": expected_text,
    }

    # ── Step 1: tokenize to vectors ──────────────────────────────────────
    t0 = time.perf_counter()
    try:
        vectors: List[TensorCoordinate] = splitter.tokenize_to_vectors(input_string)
        result["num_vectors"] = len(vectors)
        result["vectors"] = [v.vector for v in vectors]
    except Exception as exc:
        vectors = []
        result["num_vectors"] = 0
        result["vectors"] = []
        result["encode_error"] = str(exc)
    encode_ms = (time.perf_counter() - t0) * 1000

    # ── Step 2: decode vectors back to text ──────────────────────────────
    t0 = time.perf_counter()
    try:
        decoded_text: str = tokenizer.decode(vectors) if vectors else ""
        decoded_tokens = decoded_text.split() if decoded_text else []
    except Exception as exc:
        decoded_text = ""
        decoded_tokens = []
        result["decode_error"] = str(exc)
    decode_ms = (time.perf_counter() - t0) * 1000

    result["decoded_text"] = decoded_text
    result["decoded_tokens"] = decoded_tokens
    result["encode_ms"] = round(encode_ms, 3)
    result["decode_ms"] = round(decode_ms, 3)

    # ── Step 3: score ────────────────────────────────────────────────────
    exact = _exact_match(decoded_text, expected_text)
    similarity = _similarity_ratio(decoded_text, expected_text)
    tok_metrics = _token_f1(decoded_tokens, expected_tokens)

    result["exact_match"] = exact
    result["char_similarity"] = round(similarity, 4)
    result["token_precision"] = round(tok_metrics["precision"], 4)
    result["token_recall"] = round(tok_metrics["recall"], 4)
    result["token_f1"] = round(tok_metrics["f1"], 4)
    result["pass"] = exact
    result["has_error"] = "encode_error" in result or "decode_error" in result

    # ── Logging ──────────────────────────────────────────────────────────
    if verbose:
        status = "✅ PASS" if exact else "❌ FAIL"
        print(f"  ┌── {tc_id}  [{difficulty.upper()}]  {status}")
        print(f"  │   Category   : {category}")
        print(f"  │   Description: {description}")
        print(f"  │   Input      : \"{input_string}\"")
        print(f"  │   Expected   : {expected_tokens}")
        print(f"  │   Decoded    : {decoded_tokens}")
        if not exact:
            print(f"  │   Expected ↔ Decoded diff:")
            print(f"  │     expected text: \"{expected_text}\"")
            print(f"  │     decoded  text: \"{decoded_text}\"")
        print(f"  │   Vectors ({len(vectors)}):")
        for i, v in enumerate(vectors):
            try:
                word = tokenizer.decode([v])
            except Exception:
                word = "<?>"
            print(f"  │     [{i}] {word:<18} → {v.vector}")
        print(f"  │   Char Similarity : {similarity:.2%}")
        print(f"  │   Token F1        : {tok_metrics['f1']:.2%}  "
              f"(P={tok_metrics['precision']:.2%}  R={tok_metrics['recall']:.2%})")
        print(f"  │   Timing          : encode={encode_ms:.1f}ms  decode={decode_ms:.1f}ms")
        if "encode_error" in result:
            print(f"  │   ⚠ Encode Error  : {result['encode_error']}")
        if "decode_error" in result:
            print(f"  │   ⚠ Decode Error  : {result['decode_error']}")
        print(f"  └{'─' * 60}")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Aggregate reporting
# ═══════════════════════════════════════════════════════════════════════════

def _group_stats(results: List[Dict], key: str) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict]] = defaultdict(list)
    for r in results:
        groups[r[key]].append(r)

    stats: Dict[str, Dict[str, Any]] = {}
    for name, items in sorted(groups.items()):
        n = len(items)
        exact_pct = sum(1 for r in items if r["pass"]) / n if n else 0
        avg_sim = sum(r["char_similarity"] for r in items) / n if n else 0
        avg_f1 = sum(r["token_f1"] for r in items) / n if n else 0
        stats[name] = {
            "count": n,
            "exact_match_rate": round(exact_pct, 4),
            "avg_char_similarity": round(avg_sim, 4),
            "avg_token_f1": round(avg_f1, 4),
        }
    return stats


def print_summary(results: List[Dict]) -> Dict[str, Any]:
    """Prints aggregate metrics and returns a summary dict."""
    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    failed = total - passed
    errors = sum(1 for r in results if r["has_error"])

    avg_sim = sum(r["char_similarity"] for r in results) / total if total else 0
    avg_f1 = sum(r["token_f1"] for r in results) / total if total else 0
    avg_enc = sum(r["encode_ms"] for r in results) / total if total else 0
    avg_dec = sum(r["decode_ms"] for r in results) / total if total else 0

    diff_stats = _group_stats(results, "difficulty")
    cat_stats = _group_stats(results, "category")

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "exact_match_rate": round(passed / total, 4) if total else 0,
        "avg_char_similarity": round(avg_sim, 4),
        "avg_token_f1": round(avg_f1, 4),
        "avg_encode_ms": round(avg_enc, 3),
        "avg_decode_ms": round(avg_dec, 3),
        "by_difficulty": diff_stats,
        "by_category": cat_stats,
    }

    # ── Pretty-print ─────────────────────────────────────────────────────
    print("\n" + "═" * 66)
    print("  AGGREGATE RESULTS")
    print("═" * 66)
    print(f"  Total cases     : {total}")
    print(f"  Passed (exact)  : {passed}  ({summary['exact_match_rate']:.0%})")
    print(f"  Failed          : {failed}")
    print(f"  Errors          : {errors}")
    print(f"  Avg Char Sim    : {avg_sim:.2%}")
    print(f"  Avg Token F1    : {avg_f1:.2%}")
    print(f"  Avg Encode Time : {avg_enc:.1f} ms")
    print(f"  Avg Decode Time : {avg_dec:.1f} ms")

    print("\n  ── By Difficulty ──")
    header = f"  {'Difficulty':<12} {'N':>4}  {'Exact%':>7}  {'AvgSim':>7}  {'AvgF1':>7}"
    print(header)
    print("  " + "─" * len(header.strip()))
    for name, s in diff_stats.items():
        print(f"  {name:<12} {s['count']:>4}  {s['exact_match_rate']:>7.0%}  "
              f"{s['avg_char_similarity']:>7.2%}  {s['avg_token_f1']:>7.2%}")

    print("\n  ── By Category ──")
    header = f"  {'Category':<32} {'N':>4}  {'Exact%':>7}  {'AvgSim':>7}  {'AvgF1':>7}"
    print(header)
    print("  " + "─" * len(header.strip()))
    for name, s in cat_stats.items():
        print(f"  {name:<32} {s['count']:>4}  {s['exact_match_rate']:>7.0%}  "
              f"{s['avg_char_similarity']:>7.2%}  {s['avg_token_f1']:>7.2%}")

    print("═" * 66 + "\n")
    return summary


# ═══════════════════════════════════════════════════════════════════════════
# File output (CSV + JSON summary)
# ═══════════════════════════════════════════════════════════════════════════

def save_csv(results: List[Dict], path: Path) -> None:
    """Write per-case results to a CSV."""
    fields = [
        "id", "difficulty", "category", "input",
        "expected_text", "decoded_text",
        "exact_match", "char_similarity",
        "token_precision", "token_recall", "token_f1",
        "num_vectors", "encode_ms", "decode_ms",
        "has_error",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"[+] Per-case results saved → {path}")


def save_summary_json(summary: Dict, path: Path) -> None:
    """Write aggregate summary dict to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    print(f"[+] Aggregate summary saved → {path}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sanskrit Engine Grammar Test Runner",
    )
    parser.add_argument(
        "test_file",
        nargs="?",
        default=str(_PROJECT_ROOT / "tests" / "basic_grammar_tests.json"),
        help="Path to JSON test-set file (default: tests/basic_grammar_tests.json)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_PROJECT_ROOT / "tests" / "results"),
        help="Directory for output CSV / summary JSON (default: tests/results/)",
    )
    parser.add_argument(
        "--rules",
        default="data/rules/panini_ir_grammar.json",
        help="Path to Panini IR grammar rules JSON",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress per-case verbose logging (show only summary)",
    )
    args = parser.parse_args()

    # ── Load test cases ──────────────────────────────────────────────────
    test_path = Path(args.test_file)
    if not test_path.exists():
        print(f"ERROR: test file not found: {test_path}", file=sys.stderr)
        sys.exit(1)

    with open(test_path, "r", encoding="utf-8") as f:
        test_cases: List[Dict[str, Any]] = json.load(f)

    test_set_name = test_path.stem
    print(f"\n📄  Test set  : {test_path}")
    print(f"    Cases     : {len(test_cases)}")
    difficulties = sorted({tc.get('difficulty', '?') for tc in test_cases})
    print(f"    Difficulty: {', '.join(difficulties)}\n")

    # ── Init engine ──────────────────────────────────────────────────────
    # Change to project root so relative data/ paths resolve correctly
    os.chdir(_PROJECT_ROOT)
    splitter, tokenizer = init_engine(args.rules)

    # ── Run all cases ────────────────────────────────────────────────────
    results: List[Dict[str, Any]] = []
    print("─" * 66)
    print("  RUNNING TEST CASES")
    print("─" * 66)
    for tc in test_cases:
        r = run_single_test(tc, splitter, tokenizer, verbose=not args.quiet)
        results.append(r)

    # ── Summary ──────────────────────────────────────────────────────────
    summary = print_summary(results)
    summary["test_set"] = str(test_path)
    summary["timestamp"] = datetime.now().isoformat()

    # ── Save outputs ─────────────────────────────────────────────────────
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"{test_set_name}_{timestamp_tag}.csv"
    json_path = out_dir / f"{test_set_name}_{timestamp_tag}_summary.json"

    save_csv(results, csv_path)
    save_summary_json(summary, json_path)

    # ── Exit code ────────────────────────────────────────────────────────
    if summary["failed"] > 0:
        print(f"\n⚠  {summary['failed']}/{summary['total']} test(s) did not achieve exact match.")
    else:
        print(f"\n✅  All {summary['total']} test(s) passed with exact match!")

    # Return non-zero when any cases fail so CI can gate on it
    sys.exit(1 if summary["failed"] > 0 else 0)


if __name__ == "__main__":
    main()
