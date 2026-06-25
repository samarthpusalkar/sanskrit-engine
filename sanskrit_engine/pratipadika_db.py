from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from indic_transliteration import sanscript

DB_PATH = Path(__file__).parent.parent / "data" / "pratipadika.db"
JSON_FALLBACK_PATH = Path(__file__).parent.parent / "data" / "optimized_pratipadika.json"


class PratipadikaDatabase:
    """
    High-performance runtime datastore interface for Sanskrit Prātipadika (nominal stem) entries.
    Queries indexed SQLite Document Store or falls back to in-memory JSON.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._in_memory_fallback: Dict[str, Dict[str, Any]] | None = None
        self._conn: sqlite3.Connection | None = None
        self._cache: Dict[str, Dict[str, Any] | None] = {}

    def _get_connection(self) -> sqlite3.Connection | None:
        if self._conn is not None:
            return self._conn
        if self.db_path.exists():
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            return self._conn
        return None

    def _load_fallback(self) -> Dict[str, Dict[str, Any]]:
        if self._in_memory_fallback is not None:
            return self._in_memory_fallback
            
        self._in_memory_fallback = {}
        if JSON_FALLBACK_PATH.exists():
            with open(JSON_FALLBACK_PATH, "r", encoding="utf-8") as f:
                entries = json.load(f)
                for e in entries:
                    slp1 = e.get("morphology", {}).get("base_slp1")
                    if slp1:
                        self._in_memory_fallback[slp1] = e
        return self._in_memory_fallback

    def load_into_vocab(self, root_vocab: Dict[str, int], rev_root: Dict[int, str]) -> None:
        """Loads all indexed nominal stems into the runtime vocabulary dictionaries."""
        conn = self._get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT concept_id, base_iast, base_dev, base_slp1 FROM pratipadika_index")
            for cid, iast, dev, slp1 in cur.fetchall():
                if iast: root_vocab[iast] = cid
                if dev: root_vocab[dev] = cid
                if slp1: root_vocab[slp1] = cid
                rev_root[cid] = iast or slp1 or dev
            return
            
        fallback = self._load_fallback()
        for slp1, entry in fallback.items():
            cid = entry.get("vector_meta", {}).get("concept_id")
            morph = entry.get("morphology", {})
            iast = morph.get("base_iast")
            dev = morph.get("base_dev")
            if cid:
                if iast: root_vocab[iast] = cid
                if dev: root_vocab[dev] = cid
                if slp1: root_vocab[slp1] = cid
                rev_root[cid] = iast or slp1 or dev

    def get_pratipadika(self, base: str) -> Dict[str, Any] | None:
        """
        Retrieves a Prātipadika schema dictionary by exact SLP1, Devanagari, or IAST string.
        Performs sub-millisecond indexed SQL lookup with LRU/dict caching.
        """
        if not base:
            return None
            
        query_str = base.strip()
        if query_str in self._cache:
            return self._cache[query_str]
        
        conn = self._get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT d.json_content 
                FROM pratipadika_index i
                JOIN pratipadika_data d ON i.concept_id = d.concept_id
                WHERE i.base_slp1 = ? OR i.base_dev = ? OR i.base_iast = ?
            """, (query_str, query_str, query_str))
            
            row = cur.fetchone()
            if row:
                res = json.loads(row[0])
                self._cache[query_str] = res
                return res
                
            # If not found directly, try converting query to SLP1
            if not query_str.isascii():
                slp1_query = sanscript.transliterate(query_str, sanscript.DEVANAGARI, sanscript.SLP1)
                if slp1_query != query_str:
                    res = self.get_pratipadika(slp1_query)
                    self._cache[query_str] = res
                    return res
            self._cache[query_str] = None
            return None
            
        # Fallback to JSON
        fallback = self._load_fallback()
        if query_str in fallback:
            return fallback[query_str]
        slp1_q = sanscript.transliterate(query_str, sanscript.DEVANAGARI, sanscript.SLP1)
        return fallback.get(slp1_q)

    def get_by_gana(self, gana_name: str) -> List[Dict[str, Any]]:
        """
        Retrieves all Prātipadikas tagged with a specific Pāṇinian Gaṇa (e.g. 'sarvadi').
        """
        if not gana_name:
            return []
        
        clean_gana = gana_name.replace("ः", "").strip()
        results = []
        
        conn = self._get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT json_content FROM pratipadika_data")
            for row in cur:
                entry = json.loads(row[0])
                if clean_gana in entry.get("paninian_meta", {}).get("gana_tags", []):
                    results.append(entry)
            return results
            
        for e in self._load_fallback().values():
            if clean_gana in e.get("paninian_meta", {}).get("gana_tags", []):
                results.append(e)
        return results

    def get_avyayas(self) -> List[Dict[str, Any]]:
        """
        Retrieves all indeclinable Prātipadikas (is_avyaya == True).
        """
        conn = self._get_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT d.json_content 
                FROM pratipadika_index i
                JOIN pratipadika_data d ON i.concept_id = d.concept_id
                WHERE i.is_avyaya = 1
            """)
            res = [json.loads(row[0]) for row in cur.fetchall()]
            return res
            
        return [e for e in self._load_fallback().values() if e.get("paninian_meta", {}).get("is_avyaya")]

    def create_namadhatu(self, stem_or_id: str | int, suffix: str = "kyac") -> Dict[str, Any] | None:
        """
        Compiler runtime function that turns a Prātipadika (noun base) into a temporary Dhātu object.
        Applies morphological suffix (e.g., 'kyac' -> lengthens stem vowel to ī + ya) without storing verb flags on nouns.
        """
        noun = None
        if isinstance(stem_or_id, int):
            conn = self._get_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT json_content FROM pratipadika_data WHERE concept_id = ?", (stem_or_id,))
                row = cur.fetchone()
                if row:
                    noun = json.loads(row[0])
            if not noun:
                for e in self._load_fallback().values():
                    if e.get("vector_meta", {}).get("concept_id") == stem_or_id:
                        noun = e
                        break
        else:
            noun = self.get_pratipadika(str(stem_or_id))
            
        if not noun:
            return None
            
        base_slp1 = noun["morphology"]["base_slp1"]
        base_dev = noun["morphology"]["base_dev"]
        base_iast = noun["morphology"]["base_iast"]
        
        # Pāṇinian Nāmadhātu suffix rules (7.4.33 क्यचि च): final a/ā -> ī
        nam_slp1 = base_slp1
        if suffix.lower() in ("kyac", "kyan"):
            if nam_slp1.endswith("a") or nam_slp1.endswith("A"):
                nam_slp1 = nam_slp1[:-1] + "Iya"
            else:
                nam_slp1 = nam_slp1 + "ya"
        elif suffix.lower() == "kamyac":
            nam_slp1 = nam_slp1 + "kamya"
        else:
            nam_slp1 = nam_slp1 + suffix
            
        nam_dev = sanscript.transliterate(nam_slp1, sanscript.SLP1, sanscript.DEVANAGARI)
        nam_iast = sanscript.transliterate(nam_slp1, sanscript.SLP1, sanscript.IAST)
        
        cid = noun["vector_meta"]["concept_id"]
        sem_eng = noun["semantics"].get("artha_english") or base_iast
        sem_hin = noun["semantics"].get("artha_hindi") or base_dev
        
        return {
            "vector_meta": {
                "concept_id": f"namadhatu_{cid}",
                "source_pratipadika_id": cid,
                "suffix_applied": suffix
            },
            "morphology": {
                "dhatu_dev": nam_dev,
                "dhatu_iast": nam_iast,
                "dhatu_slp1": nam_slp1,
                "aupadeshik_dev": nam_dev,
                "aupadeshik_iast": nam_iast,
                "aupadeshik_slp1": nam_slp1,
                "is_ajanta": True,
                "final_phoneme": nam_slp1[-1] if nam_slp1 else "a"
            },
            "compiler_flags": {
                "gana": 1,           # Inherits Class 1 (Bhvādi) default
                "pada": "P",         # Parasmaipada
                "settva": "S",       # Seṭ
                "karma": "S",        # Sakarmaka
                "accent_type": "udatta",
                "antargana": "namadhatu"
            },
            "semantics": {
                "artha_english": f"to desire/treat like {sem_eng}",
                "artha_hindi": f"{sem_hin} की तरह आचरण करना"
            }
        }


# Singleton default database instance
_DEFAULT_DB = PratipadikaDatabase()

def get_pratipadika(base: str) -> Dict[str, Any] | None:
    return _DEFAULT_DB.get_pratipadika(base)

def create_namadhatu(stem_or_id: str | int, suffix: str = "kyac") -> Dict[str, Any] | None:
    return _DEFAULT_DB.create_namadhatu(stem_or_id, suffix)
