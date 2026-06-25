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
from .legacy_old import TemplateMorphology, RuleBasedMorphology  # legacy quarantine export


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
    def __init__(self, rule_engine_or_rules: Engine | list[Rule]) -> None:
        if isinstance(rule_engine_or_rules, list):
            self.engine = Engine(rule_engine_or_rules)
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
