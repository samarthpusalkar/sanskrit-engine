from __future__ import annotations

from dataclasses import dataclass

from .engine import Engine, EngineResult
from .rules import Rule
from .token import Token


@dataclass(frozen=True)
class EnforcementIssue:
    code: str
    message: str


@dataclass(frozen=True)
class EnforcementResult:
    input_text: str
    output_text: str
    engine_result: EngineResult
    issues: tuple[EnforcementIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


class RuleEnforcer:
    def __init__(self, rules: list[Rule], max_steps: int = 10_000) -> None:
        self.engine = Engine(rules, max_steps=max_steps)

    def enforce_text(self, text: str) -> EnforcementResult:
        tokens = [Token(part) for part in text.split()]
        return self.enforce_tokens(tokens, input_text=text)

    def enforce_tokens(self, tokens: list[Token], input_text: str | None = None) -> EnforcementResult:
        result = self.engine.process(tokens)
        issues: list[EnforcementIssue] = []
        if result.halted_reason != "stable":
            issues.append(
                EnforcementIssue(
                    "non_stable_derivation",
                    f"Engine halted with {result.halted_reason}",
                )
            )
        return EnforcementResult(
            input_text=input_text or " ".join(token.text for token in tokens),
            output_text=" ".join(token.text for token in result.tokens),
            engine_result=result,
            issues=tuple(issues),
        )
