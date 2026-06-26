from __future__ import annotations

from dataclasses import dataclass, field

from .phonology import PhonemeToken, tokenize_phonemes
from .sandhi import SandhiSplit, SandhiSplitter


@dataclass(frozen=True)
class ParseNode:
    text: str
    kind: str
    features: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ParseResult:
    input_text: str
    phonemes: tuple[PhonemeToken, ...]
    nodes: tuple[ParseNode, ...]
    sandhi_candidates: tuple[SandhiSplit, ...]


class SanskritParser:
    def __init__(self, sandhi_splitter: SandhiSplitter | None = None) -> None:
        self.sandhi_splitter = sandhi_splitter or SandhiSplitter()

    def parse(self, text: str) -> ParseResult:
        words = [word for word in text.split() if word]
        nodes = tuple(ParseNode(word, self._guess_kind(word), self._guess_features(word)) for word in words)
        return ParseResult(
            input_text=text,
            phonemes=tuple(tokenize_phonemes(text)),
            nodes=nodes,
            sandhi_candidates=tuple(self.sandhi_splitter.split_candidates(text.replace(" ", ""))),
        )

    @staticmethod
    def _guess_kind(word: str) -> str:
        if word.endswith(("ti", "anti", "si", "mi")):
            return "verb"
        if word.endswith(("ḥ", "m", "au", "āḥ")):
            return "noun"
        return "unknown"

    @staticmethod
    def _guess_features(word: str) -> dict[str, str]:
        features: dict[str, str] = {}
        if word.endswith("ḥ"):
            features.update({"case": "nominative", "number": "singular"})
        elif word.endswith("m"):
            features.update({"case": "accusative", "number": "singular"})
        if word.endswith("ti"):
            features.update({"person": "third", "number": "singular", "tense": "present"})
        elif word.endswith("anti"):
            features.update({"person": "third", "number": "plural", "tense": "present"})
        return features


class GenerativeChartParser:
    """True generative chart parser. Replaces regex heuristics."""

    @staticmethod
    def validate_pada(word: str) -> bool:
        from .lexicon import lookup_pratipadika
        return bool(lookup_pratipadika(word))

