from __future__ import annotations

from dataclasses import dataclass

from .rules import Rule


@dataclass(frozen=True)
class Match:
    rule: Rule
    index: int


class ConflictResolver:
    """Deterministic rule chooser.

    Ordering:
    1. explicit numeric priority
    2. Rajpopat-style right operand beats left operand for operand conflict
    3. structural specificity
    4. later source order
    """

    def choose(self, matches: list[Match]) -> Match:
        if not matches:
            raise ValueError("No rule matches to resolve")
        return max(matches, key=self._rank)

    @staticmethod
    def _rank(match: Match) -> tuple[int, int, int, int]:
        rule = match.rule
        operand_rank = 1 if rule.scope == "right_operand" else 0
        return (rule.priority, operand_rank, rule.specificity, rule.source_order)
