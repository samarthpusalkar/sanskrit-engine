from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Token:
    """One mutable unit on the derivation tape."""

    text: str
    tags: set[str] = field(default_factory=set)
    features: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    consumed_rules: set[str] = field(default_factory=set)

    def copy(self) -> "Token":
        return Token(
            text=self.text,
            tags=set(self.tags),
            features=dict(self.features),
            source=self.source,
            consumed_rules=set(self.consumed_rules),
        )

    def fingerprint(self) -> tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]]:
        features = tuple(sorted((k, repr(v)) for k, v in self.features.items()))
        return (self.text, tuple(sorted(self.tags)), features)


def tape_fingerprint(tokens: list[Token]) -> tuple[tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]], ...]:
    return tuple(token.fingerprint() for token in tokens)
