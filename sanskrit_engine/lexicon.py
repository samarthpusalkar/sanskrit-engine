from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NounEntry:
    stem: str
    gender: str
    gloss: str


@dataclass(frozen=True)
class VerbEntry:
    root: str
    present_stem: str
    gloss: str


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

