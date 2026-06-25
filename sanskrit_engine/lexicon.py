from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .pratipadika_db import get_pratipadika


@dataclass(frozen=True)
class NounEntry:
    stem: str
    gender: str
    gloss: str

    @classmethod
    def from_schema(cls, data: Dict[str, Any]) -> NounEntry | None:
        if not data:
            return None
        morph = data.get("morphology", {})
        pos = data.get("pos_flags", {})
        sem = data.get("semantics", {})
        
        stem = morph.get("base_slp1", "")
        genders = pos.get("allowed_genders", ["M"])
        gender_str = "masculine" if "M" in genders else ("feminine" if "F" in genders else "neuter")
        gloss = sem.get("artha_english") or sem.get("artha_hindi") or ""
        
        return cls(stem=stem, gender=gender_str, gloss=gloss)


@dataclass(frozen=True)
class VerbEntry:
    root: str
    present_stem: str
    gloss: str


def lookup_pratipadika(word: str) -> Dict[str, Any] | None:
    """
    Looks up full Prātipadika JSON schema by exact SLP1/Devanagari/IAST string.
    """
    return get_pratipadika(word)


DEFAULT_NOUNS = (
    NounEntry("rāma", "masculine", "Rama"),
    NounEntry("bāla", "masculine", "boy"),
    NounEntry("phala", "neuter", "fruit"),
    NounEntry("grāma", "masculine", "village"),
    NounEntry("jñāna", "neuter", "knowledge"),
)

DEFAULT_VERBS = (
    VerbEntry("gam", "gaccha", "go"),
    VerbEntry("paṭh", "paṭha", "read"),
    VerbEntry("khād", "khāda", "eat"),
    VerbEntry("bhū", "bhava", "become"),
)
