from __future__ import annotations

from dataclasses import dataclass

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


class TemplateMorphology:
    """Explicit v0 morphology templates.

    Real engine path: replace each template with derivation via encoded sutras.
    """

    def decline(self, noun: NounEntry, case: str, number: str) -> GeneratedForm:
        if noun.gender == "masculine" and noun.stem.endswith("a"):
            endings = {
                ("nominative", "singular"): "ḥ",
                ("accusative", "singular"): "m",
                ("nominative", "plural"): "āḥ",
            }
            ending = endings[(case, number)]
            return GeneratedForm(
                text=noun.stem + ending,
                lemma=noun.stem,
                features={"pos": "noun", "gender": noun.gender, "case": case, "number": number},
                rule_ids=("template.a_masc",),
            )
        if noun.gender == "neuter" and noun.stem.endswith("a"):
            endings = {
                ("nominative", "singular"): "m",
                ("accusative", "singular"): "m",
                ("nominative", "plural"): "āni",
            }
            ending = endings[(case, number)]
            return GeneratedForm(
                text=noun.stem + ending,
                lemma=noun.stem,
                features={"pos": "noun", "gender": noun.gender, "case": case, "number": number},
                rule_ids=("template.a_neuter",),
            )
        raise ValueError(f"Unsupported noun template: {noun}")

    def conjugate(self, verb: VerbEntry, person: str, number: str, tense: str) -> GeneratedForm:
        if tense != "present":
            raise ValueError(f"Unsupported tense: {tense}")
        endings = {
            ("third", "singular"): "ti",
            ("third", "plural"): "nti",
            ("first", "singular"): "mi",
            ("second", "singular"): "si",
        }
        ending = endings[(person, number)]
        return GeneratedForm(
            text=verb.present_stem + ending,
            lemma=verb.root,
            features={"pos": "verb", "person": person, "number": number, "tense": tense},
            rule_ids=("template.present_parasmaipada",),
        )


class RuleBasedMorphology:
    """Morphology by executing rule packs over stem + affix tokens."""

    def __init__(self, rules: list[Rule]) -> None:
        self.engine = Engine(rules)

    def decline(self, noun: NounEntry, case: str, number: str) -> GeneratedForm:
        suffix = self._sup_suffix(noun.gender, case, number)
        tokens = [
            Token(
                noun.stem,
                tags={"stem"},
                features={"pos": "noun", "gender": noun.gender, "stem_final": noun.stem[-1]},
            ),
            Token(
                suffix,
                tags={"sup"},
                features={"case": case, "number": number},
            ),
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(
            text=result.text,
            lemma=noun.stem,
            features={"pos": "noun", "gender": noun.gender, "case": case, "number": number},
            rule_ids=tuple(step.rule_id for step in result.trace),
        )

    def conjugate(self, verb: VerbEntry, person: str, number: str, tense: str) -> GeneratedForm:
        suffix = self._tin_suffix(person, number, tense)
        tokens = [
            Token(
                verb.present_stem,
                tags={"verb_stem"},
                features={"pos": "verb", "root": verb.root},
            ),
            Token(
                suffix,
                tags={"tin"},
                features={"person": person, "number": number, "tense": tense},
            ),
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(
            text=result.text,
            lemma=verb.root,
            features={"pos": "verb", "person": person, "number": number, "tense": tense},
            rule_ids=tuple(step.rule_id for step in result.trace),
        )

    @staticmethod
    def _sup_suffix(gender: str, case: str, number: str) -> str:
        supported = {
            ("masculine", "nominative", "singular"): "su",
            ("masculine", "accusative", "singular"): "am",
            ("masculine", "nominative", "plural"): "jas",
            ("neuter", "nominative", "singular"): "su",
            ("neuter", "accusative", "singular"): "am",
            ("neuter", "nominative", "plural"): "jas",
        }
        return supported[(gender, case, number)]

    @staticmethod
    def _tin_suffix(person: str, number: str, tense: str) -> str:
        if tense != "present":
            raise ValueError(f"Unsupported tense: {tense}")
        supported = {
            ("third", "singular", "present"): "tip",
            ("third", "plural", "present"): "jhi",
            ("first", "singular", "present"): "mip",
            ("second", "singular", "present"): "sip",
        }
        return supported[(person, number, tense)]
