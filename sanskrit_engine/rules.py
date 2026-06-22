from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .pratyahara import PratyaharaResolver
from .token import Token

RuleType = Literal["vidhi", "samjna", "paribhasha", "adhikara", "atidesha", "niyama"]
OperationType = Literal[
    "replace_text",
    "replace_suffix",
    "replace_prefix",
    "rewrite_boundary",
    "merge_with_right",
    "merge_text_with_right",
    "delete",
    "add_tag",
    "remove_tag",
    "set_feature",
    "noop",
]


@dataclass(frozen=True)
class Condition:
    text: str | None = None
    text_in: frozenset[str] | None = None
    text_suffix: str | None = None
    text_prefix: str | None = None
    text_contains: str | None = None
    tag: str | None = None
    has_tags: frozenset[str] = field(default_factory=frozenset)
    feature_equals: dict[str, Any] = field(default_factory=dict)
    in_pratyahara: str | None = None
    absent: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Condition | None":
        if data is None:
            return None
        return cls(
            text=data.get("text"),
            text_in=frozenset(data["text_in"]) if "text_in" in data else None,
            text_suffix=data.get("text_suffix"),
            text_prefix=data.get("text_prefix"),
            text_contains=data.get("text_contains"),
            tag=data.get("tag"),
            has_tags=frozenset(data.get("has_tags", [])),
            feature_equals=dict(data.get("feature_equals", {})),
            in_pratyahara=data.get("in_pratyahara"),
            absent=bool(data.get("absent", False)),
        )

    def matches(self, token: Token | None, pratyahara: PratyaharaResolver) -> bool:
        if self.absent:
            return token is None
        if token is None:
            return False
        if self.text is not None and token.text != self.text:
            return False
        if self.text_in is not None and token.text not in self.text_in:
            return False
        if self.text_suffix is not None and not token.text.endswith(self.text_suffix):
            return False
        if self.text_prefix is not None and not token.text.startswith(self.text_prefix):
            return False
        if self.text_contains is not None and self.text_contains not in token.text:
            return False
        if self.tag is not None and self.tag not in token.tags:
            return False
        if self.has_tags and not self.has_tags.issubset(token.tags):
            return False
        for key, value in self.feature_equals.items():
            if token.features.get(key) != value:
                return False
        if self.in_pratyahara is not None and not pratyahara.contains(self.in_pratyahara, token.text):
            return False
        return True

    @property
    def specificity(self) -> int:
        score = 0
        score += self.text is not None
        score += self.text_in is not None
        score += self.text_suffix is not None
        score += self.text_prefix is not None
        score += self.text_contains is not None
        score += self.tag is not None
        score += len(self.has_tags)
        score += len(self.feature_equals)
        score += self.in_pratyahara is not None
        return score


@dataclass(frozen=True)
class Operation:
    type: OperationType
    text: str | None = None
    old: str | None = None
    new: str | None = None
    right_old: str | None = None
    right_new: str | None = None
    joiner: str = ""
    tag: str | None = None
    feature: str | None = None
    value: Any = None
    remove_right: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Operation":
        return cls(
            type=data["type"],
            text=data.get("text"),
            old=data.get("old"),
            new=data.get("new"),
            right_old=data.get("right_old"),
            right_new=data.get("right_new"),
            joiner=data.get("joiner", ""),
            tag=data.get("tag"),
            feature=data.get("feature"),
            value=data.get("value"),
            remove_right=bool(data.get("remove_right", False)),
        )


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    type: RuleType
    priority: int
    operation: Operation
    target: Condition | None = None
    left: Condition | None = None
    right: Condition | None = None
    scope: Literal["target", "left_operand", "right_operand"] = "target"
    source_order: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_order: int) -> "Rule":
        conditions = data.get("conditions", {})
        return cls(
            id=str(data["id"]),
            name=data.get("name", str(data["id"])),
            type=data.get("type", "vidhi"),
            priority=int(data.get("priority", 0)),
            operation=Operation.from_dict(data["operation"]),
            target=Condition.from_dict(conditions.get("target")),
            left=Condition.from_dict(conditions.get("left")),
            right=Condition.from_dict(conditions.get("right")),
            scope=data.get("scope", "target"),
            source_order=source_order,
        )

    def matches(self, tokens: list[Token], index: int, pratyahara: PratyaharaResolver) -> bool:
        target = tokens[index] if 0 <= index < len(tokens) else None
        left = tokens[index - 1] if index > 0 else None
        right = tokens[index + 1] if index + 1 < len(tokens) else None
        return (
            (self.target is None or self.target.matches(target, pratyahara))
            and (self.left is None or self.left.matches(left, pratyahara))
            and (self.right is None or self.right.matches(right, pratyahara))
        )

    @property
    def specificity(self) -> int:
        return sum(
            condition.specificity
            for condition in (self.left, self.target, self.right)
            if condition is not None
        )
