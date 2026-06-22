from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SandhiSplit:
    left: str
    right: str
    rule_id: str
    confidence: float


class SandhiSplitter:
    """Small reversible sandhi splitter.

    This is seed logic. Full version should be generated from encoded rules.
    """

    def split_candidates(self, text: str) -> list[SandhiSplit]:
        candidates: list[SandhiSplit] = []
        for index, char in enumerate(text):
            if char == "ā":
                candidates.append(SandhiSplit(text[:index] + "a", "a" + text[index + 1 :], "6.1.101.sample", 0.65))
            elif char == "e":
                candidates.append(SandhiSplit(text[:index] + "a", "i" + text[index + 1 :], "6.1.87.sample", 0.45))
            elif char == "o":
                candidates.append(SandhiSplit(text[:index] + "a", "u" + text[index + 1 :], "6.1.87.sample", 0.45))
        return candidates

