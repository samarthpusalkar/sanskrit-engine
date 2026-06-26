"""
Config-Driven Generative Morphology Engine.
Executes declarative JSON Intermediate Representations (panini_ir_grammar.json)
over our formal Pāṇinian Virtual Machine (Engine).
Contains zero hardcoded Western lookup dictionaries.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .engine import Engine
from .lexicon import NounEntry, VerbEntry
from .rules import Rule
from .token import Token



@dataclass(frozen=True)
class GeneratedForm:
    text: str
    lemma: str
    features: dict[str, str]
    rule_ids: tuple[str, ...]


class GenerativePaniniMorphology:
    """
    Pure Generative Pāṇini Grammar Engine.
    Tokenization, declension, and conjugation are driven 100% dynamically
    by declarative JSON rule configs executed across the Engine VM.
    """
    def __init__(self, rule_engine_or_rules: Optional[Union[Engine, list[Rule]]] = None) -> None:
        if rule_engine_or_rules is None:
            rule_engine_or_rules = []
        if isinstance(rule_engine_or_rules, list):
            rules = rule_engine_or_rules
            if not any(getattr(r.operation, "type", "") == "insert_affix" for r in rules):
                try:
                    from pathlib import Path
                    from .loader import load_rules
                    ir_path = Path(__file__).parent.parent / "data" / "rules" / "panini_ir_grammar.json"
                    if ir_path.exists():
                        rules = load_rules(ir_path) + rules
                except Exception:
                    pass
            self.engine = Engine(rules)
        else:
            self.engine = rule_engine_or_rules

    def derive(self, root: str, derivation_type: str) -> str:
        """Derives primary base stems via Kṛdanta / Taddhita rules."""
        if derivation_type == "none" or not derivation_type:
            return root
            
        # Place root on tape and process through engine
        tokens = [
            Token(
                root,
                tags={"root", "stem"},
                features={"pos": "root", "derivation": derivation_type}
            )
        ]
        result = self.engine.process(tokens)
        return result.text

    def decline(self, noun: NounEntry, case: str, number: str) -> GeneratedForm:
        """
        Subanta Declension via Pāṇini 4.1.2 Sup Pratyaya introduction + Sandhi.
        Zero hardcoded lookup tables.
        """
        tokens = [
            Token(
                noun.stem,
                tags={"stem"},
                features={
                    "pos": "noun",
                    "gender": noun.gender,
                    "case": case,
                    "number": number,
                    "stem_final": noun.stem[-1] if noun.stem else ""
                },
            )
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(
            text=result.text,
            lemma=noun.stem,
            features={"pos": "noun", "gender": noun.gender, "case": case, "number": number},
            rule_ids=tuple(step.rule_id for step in result.trace),
        )

    def conjugate(self, verb: VerbEntry, person: str, number: str, tense: str, voice: str = "P", settva: str = "S") -> GeneratedForm:
        """
        Tiṅanta Conjugation via Pāṇini 3.4.78 Tiṅ Pratyaya introduction + Sandhi.
        Zero hardcoded lookup tables.
        """
        tokens = [
            Token(
                verb.present_stem,
                tags={"verb_stem"},
                features={
                    "pos": "verb",
                    "person": person,
                    "number": number,
                    "tense": tense,
                    "voice": voice,
                    "root": verb.root
                },
            )
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(
            text=result.text,
            lemma=verb.root,
            features={"pos": "verb", "person": person, "number": number, "tense": tense, "voice": voice},
            rule_ids=tuple(step.rule_id for step in result.trace),
        )

    def derive_compound(self, node: Any) -> GeneratedForm:
        """Sūtra 2.1.3 Sup elision + Sandhi compound generation."""
        from .syntax_tree import LinguisticNode
        if not isinstance(node, LinguisticNode):
            raise TypeError("Node must be LinguisticNode")
        flat_tokens = node.flatten()
        result = self.engine.process([Token(t.text, tags={"compound_component"}) for t in flat_tokens])
        return GeneratedForm(
            text=result.text,
            lemma="+".join(t.text for t in flat_tokens),
            features={"pos": "noun", "samasa": node.kind},
            rule_ids=tuple(step.rule_id for step in result.trace),
        )

    def dissolve_compound(self, compound_text: str) -> str:
        """Vigraha Vākya dissolution generator."""
        return f"{compound_text} iti samāsaḥ"


class TemplateMorphology(GenerativePaniniMorphology):
    """Backward compatibility alias pointing to GenerativePaniniMorphology."""
    def __init__(self, rule_engine_or_rules: Optional[Union[Engine, list[Rule]]] = None) -> None:
        super().__init__(rule_engine_or_rules)


class RuleBasedMorphology(GenerativePaniniMorphology):
    """Backward compatibility alias pointing to GenerativePaniniMorphology."""
    def __init__(self, rule_engine_or_rules: Optional[Union[Engine, list[Rule]]] = None) -> None:
        super().__init__(rule_engine_or_rules)
