#!/usr/bin/env python3
"""
Prātipadika (Noun Base) ETL & Builder Script.

Ingests nominal lists (Gaṇapāṭha, Uṇādi) and authoritative lexical dumps (Shabdapāṭha, Amara Kosha)
from GitHub repositories, normalizes them into a rich vectorizable JSON schema, deduplicates
entries using deterministic SLP1 keys, and stores them in an indexed SQLite Document Store
and optimized JSON export.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
from typing import Any, Dict, List, Optional, Set

from indic_transliteration import sanscript

# Data URLs
URL_SHABDA_DATA = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/shabda/data2.txt"
URL_SHABDA_MEANINGS = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/shabda/shabda_meanings.txt"
URL_GANAPATH = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/ganapath/data.txt"
URL_UNAADI = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/unaadi/data.txt"
URL_AMARA = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/kosha/amara.json"
URL_MW_WORDS_TEMPLATE = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/kosha/mw-{i}.json"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "pratipadika.db")
OPTIMIZED_JSON_PATH = os.path.join(DATA_DIR, "optimized_pratipadika.json")


def download_json(url: str) -> Dict[str, Any]:
    print(f"Downloading {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def determine_ending_and_slp1(dev_str: str) -> tuple[str, str, bool, str]:
    """
    Returns base_slp1, base_iast, is_ajanta, final_phoneme.
    """
    clean_dev = dev_str.strip()
    is_ajanta = not clean_dev.endswith("्")
    base_slp1 = sanscript.transliterate(clean_dev, sanscript.DEVANAGARI, sanscript.SLP1)
    base_iast = sanscript.transliterate(clean_dev, sanscript.DEVANAGARI, sanscript.IAST)
    final_phoneme = base_slp1[-1] if base_slp1 else ""
    return base_slp1, base_iast, is_ajanta, final_phoneme


def map_gender(linga_code: str) -> tuple[List[str], str, bool]:
    """
    Maps Shabda linga codes to allowed_genders list, POS category, and is_avyaya flag.
    Codes: 'P'=Pumlinga, 'S'=Strilinga, 'N'=Napumsakalinga, 'A'=Avyaya, 'T'=Trisu
    """
    if not linga_code:
        return ["M", "N"], "substantive", False
    code = linga_code.upper()
    if code == "P":
        return ["M"], "substantive", False
    elif code == "S":
        return ["F"], "substantive", False
    elif code == "N":
        return ["N"], "substantive", False
    elif code == "A":
        return [], "avyaya", True
    elif code == "T":
        return ["M", "F", "N"], "adjective", False
    else:
        return ["M", "F", "N"], "substantive", False


def extract_meanings(urlid: str, meanings_dict: Dict[str, Any]) -> tuple[str, str]:
    """
    Extracts English and Hindi glosses from shabda_meanings.txt entry.
    """
    entry = meanings_dict.get(urlid, {})
    if not entry:
        return "", ""
        
    eng_parts = []
    hin_parts = []
    
    for key, text in entry.items():
        if not isinstance(text, str):
            continue
        # Clean gloss markers like [1] ...
        clean_text = re.sub(r'\[\d+\]\s*', '', text).strip()
        if not clean_text:
            continue
            
        if "eng" in key:
            # Extract simple English definition
            parts = clean_text.split(" 1 ")
            gloss = parts[1] if len(parts) > 1 else clean_text
            eng_parts.append(gloss.strip()[:100])
        elif "hin" in key:
            parts = clean_text.split(" - ")
            gloss = parts[-1] if len(parts) > 1 else clean_text
            hin_parts.append(gloss.strip()[:100])
            
    eng_res = "; ".join(sorted(set(eng_parts)))
    hin_res = "; ".join(sorted(set(hin_parts)))
    return eng_res, hin_res


def build_pratipadika_database(include_mw: bool = False) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Ingest sources
    shabda_json = download_json(URL_SHABDA_DATA)
    meanings_json = download_json(URL_SHABDA_MEANINGS).get("data", {})
    ganapath_json = download_json(URL_GANAPATH)
    unaadi_json = download_json(URL_UNAADI)
    amara_json = download_json(URL_AMARA)
    
    db: Dict[str, Dict[str, Any]] = {}
    next_concept_id = 10001
    
    print("Processing Shabda vocabulary core...")
    for item in shabda_json.get("data", []):
        base_dev = item.get("word", "").strip()
        if not base_dev or len(base_dev) < 1:
            continue
            
        base_slp1, base_iast, is_ajanta, final_phoneme = determine_ending_and_slp1(base_dev)
        allowed_genders, category, is_avyaya = map_gender(item.get("linga", ""))
        
        urlid = item.get("urlid", "")
        m_eng, m_hin = extract_meanings(urlid, meanings_json)
        if not m_eng:
            m_eng = item.get("artha_eng", "").strip()
        if not m_hin:
            m_hin = item.get("artha_hin", "") or item.get("artha", "")
            
        if base_slp1 in db:
            existing = db[base_slp1]
            # Merge genders
            for g in allowed_genders:
                if g not in existing["pos_flags"]["allowed_genders"]:
                    existing["pos_flags"]["allowed_genders"].append(g)
            existing["pos_flags"]["allowed_genders"].sort()
            # Merge artha
            if m_eng and m_eng not in existing["semantics"]["artha_english"]:
                existing["semantics"]["artha_english"] = f"{existing['semantics']['artha_english']}; {m_eng}".strip("; ")
            if m_hin and m_hin not in existing["semantics"]["artha_hindi"]:
                existing["semantics"]["artha_hindi"] = f"{existing['semantics']['artha_hindi']}; {m_hin}".strip("; ")
        else:
            db[base_slp1] = {
                "vector_meta": {
                    "concept_id": next_concept_id,
                    "source_dictionary": "shabdapatha"
                },
                "morphology": {
                    "base_dev": base_dev,
                    "base_iast": base_iast,
                    "base_slp1": base_slp1,
                    "final_phoneme": final_phoneme,
                    "accent_pattern": "antodatta"
                },
                "pos_flags": {
                    "category": category,
                    "allowed_genders": sorted(allowed_genders),
                    "restricted_number": None
                },
                "paninian_meta": {
                    "is_avyaya": is_avyaya,
                    "gana_tags": [],
                    "is_nipata": False
                },
                "semantics": {
                    "artha_english": m_eng,
                    "artha_hindi": m_hin
                }
            }
            next_concept_id += 1

    print("Processing Gaṇapāṭha lists...")
    avyaya_ganas = {"स्वरादि", "चादि", "प्रादि", "ऊर्यादि", "साक्षादादि"}
    pronoun_ganas = {"सर्वादि"}
    
    for gana in ganapath_json.get("data", []):
        raw_name = gana.get("name", "").replace("ः", "").strip()
        words_str = gana.get("words", "")
        clean_words = re.sub(r'<[^>]+>', '', words_str)
        clean_words = re.sub(r'<i>[^<]+</i>', '', clean_words)
        tokens = re.split(r'[\s\।\॥\,]+', clean_words)
        
        is_avy = raw_name in avyaya_ganas
        is_pron = raw_name in pronoun_ganas
        
        for t in tokens:
            t_dev = t.strip()
            if not t_dev or len(t_dev) < 1:
                continue
            t_slp1, t_iast, _, t_phon = determine_ending_and_slp1(t_dev)
            
            if t_slp1 in db:
                entry = db[t_slp1]
                if raw_name not in entry["paninian_meta"]["gana_tags"]:
                    entry["paninian_meta"]["gana_tags"].append(raw_name)
                if is_avy:
                    entry["paninian_meta"]["is_avyaya"] = True
                    entry["pos_flags"]["category"] = "avyaya"
                    entry["pos_flags"]["allowed_genders"] = []
                elif is_pron:
                    entry["pos_flags"]["category"] = "pronoun"
            else:
                cat = "avyaya" if is_avy else ("pronoun" if is_pron else "substantive")
                db[t_slp1] = {
                    "vector_meta": {
                        "concept_id": next_concept_id,
                        "source_dictionary": "ganapatha"
                    },
                    "morphology": {
                        "base_dev": t_dev,
                        "base_iast": t_iast,
                        "base_slp1": t_slp1,
                        "final_phoneme": t_phon,
                        "accent_pattern": "antodatta"
                    },
                    "pos_flags": {
                        "category": cat,
                        "allowed_genders": [] if is_avy else ["M", "N"],
                        "restricted_number": None
                    },
                    "paninian_meta": {
                        "is_avyaya": is_avy,
                        "gana_tags": [raw_name],
                        "is_nipata": raw_name == "चादि"
                    },
                    "semantics": {
                        "artha_english": "",
                        "artha_hindi": ""
                    }
                }
                next_concept_id += 1

    print("Processing Uṇādi sūtras...")
    for unadi in unaadi_json.get("data", []):
        sk_text = unadi.get("sk", "")
        for slp1, entry in db.items():
            dev_word = entry["morphology"]["base_dev"]
            if len(dev_word) > 2 and dev_word in sk_text:
                if "unadi" not in entry["paninian_meta"]["gana_tags"]:
                    entry["paninian_meta"]["gana_tags"].append("unadi")
                if "unadi" not in entry["vector_meta"]["source_dictionary"]:
                    entry["vector_meta"]["source_dictionary"] += "+unadi"

    if include_mw:
        print("Ingesting Monier-Williams headwords (approx 195,000 words)...")
        for i in range(6):
            url = URL_MW_WORDS_TEMPLATE.format(i=i)
            try:
                mw_chunk = download_json(url)
                for headword in mw_chunk.get("data", {}).keys():
                    hw_dev = headword.strip()
                    if not hw_dev or len(hw_dev) < 1:
                        continue
                    hw_slp1, hw_iast, _, hw_phon = determine_ending_and_slp1(hw_dev)
                    if hw_slp1 not in db:
                        db[hw_slp1] = {
                            "vector_meta": {
                                "concept_id": next_concept_id,
                                "source_dictionary": "cdsl_mw"
                            },
                            "morphology": {
                                "base_dev": hw_dev,
                                "base_iast": hw_iast,
                                "base_slp1": hw_slp1,
                                "final_phoneme": hw_phon,
                                "accent_pattern": "antodatta"
                            },
                            "pos_flags": {
                                "category": "substantive",
                                "allowed_genders": ["M", "F", "N"],
                                "restricted_number": None
                            },
                            "paninian_meta": {
                                "is_avyaya": False,
                                "gana_tags": [],
                                "is_nipata": False
                            },
                            "semantics": {
                                "artha_english": "",
                                "artha_hindi": ""
                            }
                        }
                        next_concept_id += 1
            except Exception as e:
                print(f"Warning skipping MW chunk {i}: {e}")

    print(f"Total deduplicated Prātipadikas built: {len(db)}")
    
    # Write optimized JSON (top entries for fast loading)
    print(f"Exporting optimized JSON to {OPTIMIZED_JSON_PATH}...")
    core_entries = [v for v in db.values() if "shabdapatha" in v["vector_meta"]["source_dictionary"] or "ganapatha" in v["vector_meta"]["source_dictionary"]]
    with open(OPTIMIZED_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(core_entries, f, ensure_ascii=False, indent=2)

    # Write SQLite DB
    print(f"Building SQLite database at {SQLITE_DB_PATH}...")
    if os.path.exists(SQLITE_DB_PATH):
        os.remove(SQLITE_DB_PATH)
        
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE pratipadika_index (
            concept_id INTEGER PRIMARY KEY,
            base_slp1 TEXT UNIQUE,
            base_dev TEXT,
            base_iast TEXT,
            category TEXT,
            is_avyaya INTEGER
        )
    """)
    
    cur.execute("""
        CREATE TABLE pratipadika_data (
            concept_id INTEGER PRIMARY KEY REFERENCES pratipadika_index(concept_id),
            json_content TEXT
        )
    """)
    
    index_rows = []
    data_rows = []
    
    for entry in db.values():
        cid = entry["vector_meta"]["concept_id"]
        slp1 = entry["morphology"]["base_slp1"]
        dev = entry["morphology"]["base_dev"]
        iast = entry["morphology"]["base_iast"]
        cat = entry["pos_flags"]["category"]
        is_avy = 1 if entry["paninian_meta"]["is_avyaya"] else 0
        
        index_rows.append((cid, slp1, dev, iast, cat, is_avy))
        data_rows.append((cid, json.dumps(entry, ensure_ascii=False)))
        
    cur.executemany("INSERT INTO pratipadika_index VALUES (?, ?, ?, ?, ?, ?)", index_rows)
    cur.executemany("INSERT INTO pratipadika_data VALUES (?, ?)", data_rows)
    
    cur.execute("CREATE INDEX idx_base_slp1 ON pratipadika_index(base_slp1)")
    cur.execute("CREATE INDEX idx_base_dev ON pratipadika_index(base_dev)")
    cur.execute("CREATE INDEX idx_category ON pratipadika_index(category)")
    cur.execute("CREATE INDEX idx_is_avyaya ON pratipadika_index(is_avyaya)")
    
    conn.commit()
    conn.close()
    print("Database build complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Sanskrit Prātipadika Database")
    parser.add_argument("--include-mw", action="store_true", help="Include 195,000+ Monier-Williams headwords")
    args = parser.parse_args()
    build_pratipadika_database(include_mw=args.include_mw)
