from __future__ import annotations

from typing import Literal, Optional

try:
    from indic_transliteration import sanscript
except ImportError:
    sanscript = None

ScriptScheme = Literal["devanagari", "iast", "slp1", "hk"]


class TransliterationFST:
    """Universal script normalization FST layer.
    
    Decouples surface orthography (Devanagari, IAST, SLP1) from internal articulatory tape cells.
    """

    SCHEME_MAP = {
        "devanagari": getattr(sanscript, "DEVANAGARI", "devanagari"),
        "iast": getattr(sanscript, "IAST", "iast"),
        "slp1": getattr(sanscript, "SLP1", "slp1"),
        "hk": getattr(sanscript, "HK", "hk"),
    }

    @classmethod
    def normalize_to_slp1(cls, text: str, source_scheme: Optional[ScriptScheme] = None) -> str:
        """Converts any surface Sanskrit text cleanly into standard internal 1-char SLP1 representation."""
        if not text:
            return ""
        if sanscript is None:
            return text

        if source_scheme is None:
            source_scheme = cls.detect_scheme(text)

        src = cls.SCHEME_MAP.get(source_scheme, sanscript.DEVANAGARI)
        if src == sanscript.SLP1:
            return text
        return str(sanscript.transliterate(text, src, sanscript.SLP1))

    @classmethod
    def format_from_slp1(cls, slp1_text: str, target_scheme: ScriptScheme = "devanagari") -> str:
        """Converts internal SLP1 tape string back into target user script."""
        if not slp1_text or sanscript is None:
            return slp1_text
        tgt = cls.SCHEME_MAP.get(target_scheme, sanscript.DEVANAGARI)
        if tgt == sanscript.SLP1:
            return slp1_text
        return str(sanscript.transliterate(slp1_text, sanscript.SLP1, tgt))

    @staticmethod
    def detect_scheme(text: str) -> ScriptScheme:
        """Heuristic scheme detection."""
        if any("\u0900" <= c <= "\u097F" for c in text):
            return "devanagari"
        if any(c in "āīūṛṝḷḹṅñṭḍṇśṣṃḥ" for c in text):
            return "iast"
        if any(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in text):
            return "slp1"
        return "iast"
