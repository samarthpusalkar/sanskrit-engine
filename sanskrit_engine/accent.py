from __future__ import annotations

from typing import List, Literal

from .phoneme import AccentType, Phoneme, TapeCell

# Svara rules based on Pāṇini 1.2.29 - 1.2.32
# Udātta (High pitch), Anudātta (Low pitch), Svarita (Falling pitch)


class VedicAccentEngine:
    """Formal Vedic Accent (Svara) assignment & Sandhi dynamics processor."""

    @staticmethod
    def assign_dhātu_accent(phonemes: List[Phoneme], is_anudātteta: bool = False) -> None:
        """Assigns Dhātu accent (Dhātoḥ 6.1.162: initial vowel is Udātta unless marked otherwise)."""
        from .phonology import is_vowel
        for p in phonemes:
            if is_vowel(p.char):
                p.accent = "A" if is_anudātteta else "U"
                break

    @staticmethod
    def assign_suffix_accent(phonemes: List[Phoneme], suffix_tags: set[str]) -> None:
        """Assigns Pratyaya accent (Ādyudāttaś ca 3.1.3: suffix initial vowel is Udātta)."""
        from .phonology import is_vowel
        # Tit suffixes have Svarita (Titisvaritaḥ 6.1.185)
        accent_val: AccentType = "S" if "tit" in suffix_tags else ("A" if "pit" in suffix_tags else "U")
        for p in phonemes:
            if is_vowel(p.char):
                p.accent = accent_val
                break

    @staticmethod
    def apply_svara_sandhi(cells: List[TapeCell]) -> None:
        """Resolves tonal Sandhi across phoneme cells.
        
        Rules:
        1. Udātta + Anudātta -> Udātta (Ekaḥ pūrvaparayor udāttaḥ 8.2.5)
        2. Udātta followed by Anudātta converts the Anudātta to Svarita (Udāttād anudāttasya svaritaḥ 8.4.66)
        """
        phonemes = [c for c in cells if isinstance(c, Phoneme)]
        for i in range(len(phonemes) - 1):
            curr = phonemes[i]
            nxt = phonemes[i + 1]
            if curr.accent == "U" and nxt.accent == "A":
                nxt.accent = "S"
