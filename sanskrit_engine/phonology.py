from __future__ import annotations

from dataclasses import dataclass


SURFACE_PHONEMES = (
    "ai",
    "au",
    "kh",
    "gh",
    "ch",
    "jh",
    "ṭh",
    "ḍh",
    "th",
    "dh",
    "ph",
    "bh",
    "ā",
    "ī",
    "ū",
    "ṛ",
    "ṝ",
    "ḷ",
    "ṃ",
    "ḥ",
    "ñ",
    "ṅ",
    "ṇ",
    "ś",
    "ṣ",
    "a",
    "i",
    "u",
    "e",
    "o",
    "k",
    "g",
    "c",
    "j",
    "ṭ",
    "ḍ",
    "t",
    "d",
    "p",
    "b",
    "m",
    "y",
    "r",
    "l",
    "v",
    "s",
    "h",
)

DEVANAGARI_PHONEMES = SURFACE_PHONEMES

VOWELS = frozenset({"a", "ā", "i", "ī", "u", "ū", "ṛ", "ṝ", "ḷ", "e", "o", "ai", "au"})


@dataclass(frozen=True)
class PhonemeToken:
    value: str
    index: int
    kind: str


def tokenize_phonemes(text: str) -> list[PhonemeToken]:
    """Greedy IAST-ish phoneme tokenizer.

    v0 uses romanized IAST because engine sample rules are romanized.
    Devanagari support should be a script-normalization layer above this.
    """

    tokens: list[PhonemeToken] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        match = None
        for phoneme in SURFACE_PHONEMES:
            if text.startswith(phoneme, index):
                match = phoneme
                break
        if match is None:
            match = text[index]
        kind = "vowel" if match in VOWELS else "consonant"
        tokens.append(PhonemeToken(match, index, kind))
        index += len(match)
    return tokens


def is_vowel(value: str) -> bool:
    return value in VOWELS

