"""
Tiṅanta Database Loader: Provides O(1) lookup for pre-compiled verb conjugations
and Kṛdanta (verbal derivative) forms from tiṅanta.db.

This module is loaded at startup by TensorTokenizer for instant morphological
recognition of ALL lakāras including destructive forms (Liṭ, Laṅ, Luṅ).
"""
import os
import sqlite3
from typing import Optional, Dict


class TingantaDB:
    """SQLite-backed lookup for pre-compiled tiṅanta and kṛdanta forms."""

    def __init__(self, db_path: str = None):
        base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.db_path = db_path or os.path.join(base_dir, "tiṅanta.db")
        self._conn = None
        self._verb_cache: Dict[str, dict] = {}
        self._krdanta_cache: Dict[str, dict] = {}
        self._rev_verb_cache: Dict[tuple, str] = {}
        self._rev_krdanta_cache: Dict[tuple, str] = {}
        self._load()

    def _load(self):
        """Load entire database into memory for O(1) dict lookups."""
        if not os.path.exists(self.db_path):
            return

        self._conn = sqlite3.connect(self.db_path)
        c = self._conn.cursor()

        # Load tiṅanta forms
        try:
            for row in c.execute("SELECT surface_form, concept_id, lakara, purusa, vacana, pada, root_iast FROM tinganta_forms"):
                surface, cid, lakara, purusa, vacana, pada, root = row
                if surface not in self._verb_cache:
                    self._verb_cache[surface] = {
                        "concept_id": cid,
                        "lakara": lakara,
                        "purusa": purusa,
                        "vacana": vacana,
                        "pada": pada,
                        "root_iast": root,
                    }
                # For reverse lookup, prefer Parasmaipada (or first seen)
                rev_key = (cid, lakara, purusa, vacana)
                if rev_key not in self._rev_verb_cache:
                    self._rev_verb_cache[rev_key] = surface
        except sqlite3.OperationalError:
            pass

        # Load kṛdanta forms
        try:
            for row in c.execute("SELECT surface_form, concept_id, derivation, root_iast FROM krdanta_forms"):
                surface, cid, derivation, root = row
                if surface not in self._krdanta_cache:
                    self._krdanta_cache[surface] = {
                        "concept_id": cid,
                        "derivation": derivation,
                        "root_iast": root,
                    }
                rev_key = (cid, derivation)
                if rev_key not in self._rev_krdanta_cache:
                    self._rev_krdanta_cache[rev_key] = surface
        except sqlite3.OperationalError:
            pass

        self._conn.close()
        self._conn = None

    def lookup_verb_form(self, surface: str) -> Optional[dict]:
        """Look up a surface verb form. Returns dict with concept_id, lakara, purusa, vacana, pada, root_iast."""
        return self._verb_cache.get(surface)

    def lookup_krdanta(self, surface: str) -> Optional[dict]:
        """Look up a kṛdanta (verbal derivative) form. Returns dict with concept_id, derivation, root_iast."""
        return self._krdanta_cache.get(surface)

    def lookup_surface_verb(self, cid: int, lakara: int, purusa: int, vacana: int) -> Optional[str]:
        """Look up surface verb string by coordinate IDs."""
        return self._rev_verb_cache.get((cid, lakara, purusa, vacana))

    def lookup_surface_krdanta(self, cid: int, derivation: int) -> Optional[str]:
        """Look up surface kṛdanta string by coordinate IDs."""
        return self._rev_krdanta_cache.get((cid, derivation))

    @property
    def verb_count(self) -> int:
        return len(self._verb_cache)

    @property
    def krdanta_count(self) -> int:
        return len(self._krdanta_cache)

    def get_dhatu(self, root_str: str) -> Optional[dict]:
        """Fetch raw Dhātu object with inherent Pāṇinian anubandha tags."""
        for meta in self._verb_cache.values():
            if meta["root_iast"] == root_str:
                return {
                    "dhatu": root_str,
                    "concept_id": meta["concept_id"],
                    "pada": meta["pada"],
                    "tags": {"udatta", "parasmaipada" if meta["pada"] == 1 else "atmanepada"},
                }
        return None
