"""
Pāṇinian Moraic & Accented Phoneme Tape Representation.
Replaces flat strings with granular phonetic objects tracking mātrā (mora), svara (accent), sthāna (place), and anubandha flags.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Union

AccentType = Literal["U", "A", "S", "None"]  # Udātta, Anudātta, Svarita, None
SthanaType = Literal["kantha", "talu", "murdha", "danta", "ostha", "nasika", "kanthatalu", "kanthostha", "dantostha", "consonant"]

# Mapping phonemes to their traditional articulatory sthāna (place)
STHANA_MAP: dict[str, SthanaType] = {
    "a": "kantha", "ā": "kantha", "h": "kantha", "ḥ": "kantha",
    "k": "kantha", "kh": "kantha", "g": "kantha", "gh": "kantha", "ṅ": "kantha",
    "i": "talu", "ī": "talu", "y": "talu", "ś": "talu",
    "c": "talu", "ch": "talu", "j": "talu", "jh": "talu", "ñ": "talu",
    "ṛ": "murdha", "ṝ": "murdha", "r": "murdha", "ṣ": "murdha",
    "ṭ": "murdha", "ṭh": "murdha", "ḍ": "murdha", "ḍh": "murdha", "ṇ": "murdha",
    "ḷ": "danta", "l": "danta", "s": "danta",
    "t": "danta", "th": "danta", "d": "danta", "dh": "danta", "n": "danta",
    "u": "ostha", "ū": "ostha",
    "p": "ostha", "ph": "ostha", "b": "ostha", "bh": "ostha", "m": "ostha",
    "e": "kanthatalu", "ai": "kanthatalu",
    "o": "kanthostha", "au": "kanthostha",
    "v": "dantostha",
    "ṃ": "nasika",
}

DIRGHA_VOWELS = frozenset({"ā", "ī", "ū", "ṝ", "e", "ai", "o", "au"})
HRASVA_VOWELS = frozenset({"a", "i", "u", "ṛ", "ḷ"})


@dataclass
class Phoneme:
    """Atomic phonetic cell on the VM tape."""
    char: str
    mora: float = 1.0  # 1.0 = hrasva, 2.0 = dīrgha, 3.0 = pluta, 0.5 = consonant
    accent: AccentType = "None"
    sthana: str = "kantha"
    prayatna: str = "vivrita"
    it_marker: bool = False  # True if silent Anubandha tag

    @classmethod
    def from_char(cls, char: str, it_marker: bool = False, accent: AccentType = "None") -> Phoneme:
        sthana = STHANA_MAP.get(char, "kantha")
        if char in DIRGHA_VOWELS:
            mora = 2.0
            prayatna = "vivrita"
        elif char in HRASVA_VOWELS:
            mora = 1.0
            prayatna = "vivrita" if char != "a" else "samvrita"
        else:
            mora = 0.5
            prayatna = "sprishta"
        return cls(char=char, mora=mora, accent=accent, sthana=sthana, prayatna=prayatna, it_marker=it_marker)


@dataclass
class MorphemeBoundary:
    """Sentinel cell indicating grammatical boundaries (+ for base-suffix, # for pada)."""
    kind: Literal["+", "#", "-"]
    char: str = field(init=False)

    def __post_init__(self) -> None:
        self.char = self.kind


TapeCell = Union[Phoneme, MorphemeBoundary]


def string_to_tape(text: str) -> list[TapeCell]:
    """Converts a raw string (e.g., 'ram+a') into a granular phoneme tape."""
    from .phonology import DEVANAGARI_PHONEMES
    cells: list[TapeCell] = []
    idx = 0
    while idx < len(text):
        if text[idx] in ("+", "#", "-"):
            cells.append(MorphemeBoundary(kind=text[idx])) # type: ignore
            idx += 1
            continue
        match = None
        for ph in DEVANAGARI_PHONEMES:
            if text.startswith(ph, idx):
                match = ph
                break
        if match is None:
            match = text[idx]
        cells.append(Phoneme.from_char(match))
        idx += len(match)
    return cells


def tape_to_string(cells: list[TapeCell], include_boundaries: bool = False, include_it: bool = False) -> str:
    """Renders tape back to string."""
    res = []
    for cell in cells:
        if isinstance(cell, MorphemeBoundary):
            if include_boundaries:
                res.append(cell.char)
        else:
            if cell.it_marker and not include_it:
                continue
            res.append(cell.char)
    return "".join(res)
