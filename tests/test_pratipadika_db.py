import pytest
import time
from sanskrit_engine.pratipadika_db import PratipadikaDatabase, get_pratipadika, create_namadhatu
from sanskrit_engine.lexicon import NounEntry, lookup_pratipadika


def test_pratipadika_ajanta_lookup():
    """Test lookup of Ajanta (vowel-ending) Prātipadika 'putra'."""
    res = get_pratipadika("putra")
    assert res is not None
    assert res["morphology"]["base_slp1"] == "putra"
    assert res["morphology"]["final_phoneme"] == "a"
    assert "M" in res["pos_flags"]["allowed_genders"]
    assert res["pos_flags"]["category"] == "substantive"
    assert res["paninian_meta"]["is_avyaya"] is False
    # Ensure zero verb metadata flags are present
    assert "dhātupāṭha" not in res.get("vector_meta", {}).get("source_dictionary", "")
    assert "class" not in res.get("pos_flags", {})


def test_pratipadika_devanagari_and_iast_lookup():
    """Test lookup by Devanagari and IAST strings."""
    res_dev = get_pratipadika("मित्र")
    res_iast = get_pratipadika("mitra")
    res_slp = get_pratipadika("mitra")
    
    assert res_dev is not None
    assert res_iast is not None
    assert res_slp == res_dev == res_iast
    # Mitra can be masculine (Sun) or neuter (Friend)
    genders = res_slp["pos_flags"]["allowed_genders"]
    assert "M" in genders or "N" in genders


def test_pratipadika_avyaya_lookup():
    """Test lookup of indeclinables (Avyaya)."""
    db = PratipadikaDatabase()
    avyayas = db.get_avyayas()
    assert len(avyayas) > 0
    
    # E.g. 'svar' or 'punar'
    res = get_pratipadika("svar")
    if res:
        assert res["paninian_meta"]["is_avyaya"] is True
        assert res["pos_flags"]["category"] == "avyaya"


def test_pratipadika_gana_search():
    """Test retrieving words by Pāṇinian Gaṇa tag."""
    db = PratipadikaDatabase()
    sarvadis = db.get_by_gana("सर्वादि")
    assert len(sarvadis) > 0
    bases = [x["morphology"]["base_slp1"] for x in sarvadis]
    assert "sarva" in bases
    assert "viSva" in bases or "viSva" in [x["morphology"]["base_iast"] for x in sarvadis]


def test_noun_entry_wrapper():
    """Test NounEntry dataclass compatibility."""
    data = lookup_pratipadika("rāma") or lookup_pratipadika("rAma")
    assert data is not None
    entry = NounEntry.from_schema(data)
    assert entry is not None
    assert entry.stem == "rAma"
    assert entry.gender == "masculine"


def test_query_speed_benchmark():
    """Benchmark indexed SQL lookup speed (< 1 ms)."""
    db = PratipadikaDatabase()
    start = time.perf_counter()
    for _ in range(100):
        db.get_pratipadika("putra")
        db.get_pratipadika("mitra")
        db.get_pratipadika("sarva")
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / 300) * 1000
    print(f"\nAverage Pratipadika query time: {avg_ms:.4f} ms")
    assert avg_ms < 1.0  # Sub-millisecond guarantee


def test_namadhatu_runtime_generation():
    """Verify runtime denominative verb (Nāmadhātu) generation from nominal stem 'putra'."""
    dhatu = create_namadhatu("putra", suffix="kyac")
    assert dhatu is not None
    # Check transformed stem: putra + kyac -> putrīya (putrIya)
    assert dhatu["morphology"]["dhatu_slp1"] == "putrIya"
    assert dhatu["compiler_flags"]["gana"] == 1
    assert dhatu["compiler_flags"]["pada"] == "P"
    assert dhatu["compiler_flags"]["settva"] == "S"
    assert dhatu["compiler_flags"]["antargana"] == "namadhatu"
    # Verify the original noun database still has zero verb flags
    putra_noun = get_pratipadika("putra")
    assert "class" not in putra_noun["pos_flags"]
    assert putra_noun["morphology"]["accent_pattern"] == "antodatta"

