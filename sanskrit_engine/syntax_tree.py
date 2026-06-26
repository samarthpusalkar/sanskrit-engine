from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Union

from .token import Token

SamasaType = Literal["avyayibhava", "tatpurusha", "karmadharaya", "dvigu", "bahuvrihi", "dvandva", "simple"]


@dataclass
class LinguisticNode:
    """Recursive Algebraic Data Type representing Pāṇinian compound structure & hierarchical derivation."""

    kind: SamasaType
    left: Union["LinguisticNode", Token, None] = None
    right: Union["LinguisticNode", Token, None] = None
    vigraha_vakya: str = "" # Dissolution sentence (e.g. rājño puruṣaḥ)
    features: dict[str, Any] = field(default_factory=dict)
    pada_boundary: bool = False

    @property
    def is_leaf(self) -> bool:
        return isinstance(self.left, Token) and self.right is None

    def flatten(self) -> list[Token]:
        """Flattens compound hierarchy into linear tape of tokens."""
        tokens: list[Token] = []
        if isinstance(self.left, LinguisticNode):
            tokens.extend(self.left.flatten())
        elif isinstance(self.left, Token):
            tokens.append(self.left)

        if isinstance(self.right, LinguisticNode):
            tokens.extend(self.right.flatten())
        elif isinstance(self.right, Token):
            tokens.append(self.right)
        return tokens

    def fingerprint(self) -> str:
        if self.is_leaf and isinstance(self.left, Token):
            return self.left.text
        l_fp = self.left.fingerprint() if isinstance(self.left, LinguisticNode) else getattr(self.left, "text", "")
        r_fp = self.right.fingerprint() if isinstance(self.right, LinguisticNode) else getattr(self.right, "text", "")
        return f"[{self.kind}:{l_fp}+{r_fp}]"
