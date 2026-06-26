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


class PaninianConflictResolver(ConflictResolver):
    """Classical 4-Tier Paribhāṣā Vyākaraṇa conflict resolver.

    Implements formal resolution principles:
    1. Apavāda over Utsarga (Specific exception overrides general).
    2. Nitya over Anitya (Indestructible applicability).
    3. Antaraṅga over Bahiraṅga (Internal over external scope).
    4. Rajpopat Right-Operand Precedence (1.4.2 Vipratiṣedhe paraṃ kāryam: Right-side morpheme operations beat left-side operations).
    """

    def resolve(self, matches: list[Match]) -> Match:
        if not matches:
            raise ValueError("No matches to resolve")
        if len(matches) == 1:
            return matches[0]
        return max(matches, key=lambda m: self._panini_rank(m, matches))

    def _panini_rank(
        self, match: Match, all_matches: list[Match]
    ) -> tuple[int, int, int, int, int]:
        rule = match.rule

        # Tier 1: Apavāda (Specificity check: is this rule an exception/more specific?)
        is_apavada = (
            1
            if rule.type == "apavada"
            or any(
                rule.specificity > other.rule.specificity
                for other in all_matches
                if other.rule.id != rule.id
            )
            else 0
        )

        # Tier 2: Nitya check (Does this rule apply regardless?)
        is_nitya = (
            1 if getattr(rule.operation, "remove_right", False) or rule.priority > 105 else 0
        )

        # Tier 3: Antaraṅga & Rajpopat Right-Operand Precedence (1.4.2)
        scope_rank = (
            3
            if rule.scope == "right_operand"
            else (2 if rule.scope == "target" else (1 if rule.scope == "left_operand" else 0))
        )

        return (is_apavada, is_nitya, scope_rank, rule.priority, rule.source_order)
