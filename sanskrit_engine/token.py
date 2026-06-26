from __future__ import annotations

import copy as _copy
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .phoneme import TapeCell


class Token:
    """One mutable unit on the derivation tape, wrapping moraic Phoneme cells."""

    def __init__(
        self,
        text: str,
        tags: set[str] | None = None,
        features: dict[str, Any] | None = None,
        source: str | None = None,
        consumed_rules: set[str] | None = None,
        cells: list[Any] | None = None,
    ) -> None:
        self.tags = tags if tags is not None else set()
        self.features = features if features is not None else {}
        self.source = source
        self.consumed_rules = consumed_rules if consumed_rules is not None else set()
        if cells is not None:
            self.cells = cells
            from .phoneme import tape_to_string
            self._text = tape_to_string(cells)
        else:
            self.text = text

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, val: str) -> None:
        self._text = val
        from .phoneme import string_to_tape
        self.cells = string_to_tape(val)

    def sync_from_cells(self) -> None:
        """Synchronizes surface .text string from internal .cells array."""
        from .phoneme import tape_to_string
        self.text = tape_to_string(self.cells, include_boundaries=False)

    def copy(self) -> "Token":
        return Token(
            text=self.text,
            tags=set(self.tags),
            features=dict(self.features),
            source=self.source,
            consumed_rules=set(self.consumed_rules),
            cells=_copy.deepcopy(self.cells) if self.cells else None,
        )

    def fingerprint(self) -> tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], tuple[Any, ...]]:
        features = tuple(sorted((k, repr(v)) for k, v in self.features.items()))
        cell_state = tuple(
            (c.char, getattr(c, "mora", 0), getattr(c, "accent", "None")) for c in self.cells
        ) if self.cells else ()
        return (self.text, tuple(sorted(self.tags)), features, cell_state)

    def __repr__(self) -> str:
        return f"Token(text={self.text!r}, tags={self.tags!r}, features={self.features!r})"


def tape_fingerprint(tokens: list[Token]) -> tuple[Any, ...]:
    return tuple(token.fingerprint() for token in tokens)
