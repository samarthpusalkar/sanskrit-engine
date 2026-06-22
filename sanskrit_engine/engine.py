from __future__ import annotations

from dataclasses import dataclass, field

from .conflict import ConflictResolver, Match
from .pratyahara import PratyaharaResolver
from .rules import Rule
from .token import Token, tape_fingerprint


@dataclass
class TraceStep:
    rule_id: str
    rule_name: str
    index: int
    before: tuple
    after: tuple


@dataclass
class EngineResult:
    tokens: list[Token]
    trace: list[TraceStep] = field(default_factory=list)
    halted_reason: str = "stable"

    @property
    def text(self) -> str:
        return "".join(token.text for token in self.tokens)


class Engine:
    def __init__(
        self,
        rules: list[Rule],
        pratyahara: PratyaharaResolver | None = None,
        conflict_resolver: ConflictResolver | None = None,
        max_steps: int = 10_000,
    ) -> None:
        self.rules = rules
        self.pratyahara = pratyahara or PratyaharaResolver()
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self.max_steps = max_steps

    def process(self, tokens: list[Token]) -> EngineResult:
        state = [token.copy() for token in tokens]
        trace: list[TraceStep] = []
        seen = {tape_fingerprint(state)}

        for _ in range(self.max_steps):
            matches = self._find_matches(state)
            if not matches:
                return EngineResult(state, trace, "stable")

            chosen = self.conflict_resolver.choose(matches)
            before = tape_fingerprint(state)
            self._apply(chosen.rule, state, chosen.index)
            after = tape_fingerprint(state)

            trace.append(
                TraceStep(
                    rule_id=chosen.rule.id,
                    rule_name=chosen.rule.name,
                    index=chosen.index,
                    before=before,
                    after=after,
                )
            )

            if after in seen:
                return EngineResult(state, trace, "cycle_detected")
            seen.add(after)

        return EngineResult(state, trace, "max_steps")

    def _find_matches(self, tokens: list[Token]) -> list[Match]:
        matches: list[Match] = []
        for index in range(len(tokens)):
            for rule in self.rules:
                if rule.matches(tokens, index, self.pratyahara):
                    matches.append(Match(rule, index))
        return matches

    def _apply(self, rule: Rule, tokens: list[Token], index: int) -> None:
        op = rule.operation
        token = tokens[index]

        if op.type == "noop":
            return
        if op.type == "replace_text":
            if op.text is None:
                raise ValueError(f"Rule {rule.id} replace_text missing text")
            token.text = op.text
            return
        if op.type == "replace_suffix":
            if op.old is None or op.new is None:
                raise ValueError(f"Rule {rule.id} replace_suffix missing old/new")
            if not token.text.endswith(op.old):
                raise ValueError(f"Rule {rule.id} suffix mismatch")
            token.text = token.text[: -len(op.old)] + op.new if op.old else token.text + op.new
            return
        if op.type == "replace_prefix":
            if op.old is None or op.new is None:
                raise ValueError(f"Rule {rule.id} replace_prefix missing old/new")
            if not token.text.startswith(op.old):
                raise ValueError(f"Rule {rule.id} prefix mismatch")
            token.text = op.new + token.text[len(op.old) :]
            return
        if op.type == "rewrite_boundary":
            if op.old is None or op.new is None or op.right_old is None or op.right_new is None:
                raise ValueError(f"Rule {rule.id} rewrite_boundary missing old/new/right_old/right_new")
            if index + 1 >= len(tokens):
                raise ValueError(f"Rule {rule.id} rewrite_boundary missing right token")
            right = tokens[index + 1]
            if not token.text.endswith(op.old):
                raise ValueError(f"Rule {rule.id} boundary suffix mismatch")
            if not right.text.startswith(op.right_old):
                raise ValueError(f"Rule {rule.id} boundary prefix mismatch")
            left_text = token.text[: -len(op.old)] + op.new if op.old else token.text + op.new
            right_text = op.right_new + right.text[len(op.right_old) :]
            if op.remove_right:
                token.text = left_text + op.joiner + right_text
                del tokens[index + 1]
            else:
                token.text = left_text
                right.text = right_text
            return
        if op.type == "merge_with_right":
            if op.text is None:
                raise ValueError(f"Rule {rule.id} merge_with_right missing text")
            token.text = op.text
            if op.remove_right:
                del tokens[index + 1]
            return
        if op.type == "merge_text_with_right":
            token.text = token.text + tokens[index + 1].text
            if op.remove_right:
                del tokens[index + 1]
            return
        if op.type == "delete":
            del tokens[index]
            return
        if op.type == "add_tag":
            if op.tag is None:
                raise ValueError(f"Rule {rule.id} add_tag missing tag")
            token.tags.add(op.tag)
            return
        if op.type == "remove_tag":
            if op.tag is None:
                raise ValueError(f"Rule {rule.id} remove_tag missing tag")
            token.tags.discard(op.tag)
            return
        if op.type == "set_feature":
            if op.feature is None:
                raise ValueError(f"Rule {rule.id} set_feature missing feature")
            token.features[op.feature] = op.value
            return

        raise ValueError(f"Unsupported operation: {op.type}")
