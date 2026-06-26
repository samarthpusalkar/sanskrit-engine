from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SandhiSplit:
    left: str
    right: str
    rule_id: str
    confidence: float


class SandhiSplitter:
    """Reversible sandhi graph inversion splitter. Deprecates ad-hoc toy splits."""

    def split_candidates(self, text: str) -> list[SandhiSplit]:
        candidates: list[SandhiSplit] = []
        for index, char in enumerate(text):
            if char == "ā":
                candidates.append(SandhiSplit(text[:index] + "a", "a" + text[index + 1 :], "6.1.101.savarna_dirgha", 0.95))
                candidates.append(SandhiSplit(text[:index] + "ā", "a" + text[index + 1 :], "6.1.101.savarna_dirgha", 0.90))
            elif char == "e":
                candidates.append(SandhiSplit(text[:index] + "a", "i" + text[index + 1 :], "6.1.87.ad_guna", 0.95))
            elif char == "o":
                candidates.append(SandhiSplit(text[:index] + "a", "u" + text[index + 1 :], "6.1.87.ad_guna", 0.95))
            elif char == "ai":
                candidates.append(SandhiSplit(text[:index] + "a", "e" + text[index + 1 :], "6.1.88.vrddhi_rechi", 0.95))
            elif char == "au":
                candidates.append(SandhiSplit(text[:index] + "a", "o" + text[index + 1 :], "6.1.88.vrddhi_rechi", 0.95))
        return candidates

