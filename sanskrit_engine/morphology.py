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

    def conjugate(self, verb: VerbEntry, person: str, number: str, tense: str, voice: str = "P") -> GeneratedForm:
        suffix = self._tin_suffix(person, number, tense, voice)
        tokens = [
            Token(
                verb.present_stem,
                tags={"verb_stem"},
                features={"pos": "verb", "root": verb.root},
            ),
            Token(
                suffix,
                tags={"tin"},
                features={"person": person, "number": number, "tense": tense, "voice": voice},
            ),
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(
            text=result.text,
            lemma=verb.root,
            features={"pos": "verb", "person": person, "number": number, "tense": tense, "voice": voice},
            rule_ids=tuple(step.rule_id for step in result.trace),
        )

    @staticmethod
    def _sup_suffix(gender: str, case: str, number: str) -> str:
        supported = {
            ("masculine", "nominative", "singular"): "su",
            ("masculine", "accusative", "singular"): "am",
            ("masculine", "instrumental", "singular"): "ṭā",
            ("masculine", "dative", "singular"): "ṅe",
            ("masculine", "genitive", "singular"): "ṅas",
            ("masculine", "locative", "singular"): "ṅi",
            ("masculine", "nominative", "plural"): "jas",
            ("masculine", "accusative", "plural"): "śas",
            ("neuter", "nominative", "singular"): "su",
            ("neuter", "accusative", "singular"): "am",
            ("neuter", "instrumental", "singular"): "ṭā",
            ("neuter", "dative", "singular"): "ṅe",
            ("neuter", "genitive", "singular"): "ṅas",
            ("neuter", "locative", "singular"): "ṅi",
            ("neuter", "nominative", "plural"): "jas",
            ("neuter", "accusative", "plural"): "śas",
        }
        return supported[(gender, case, number)]

    @staticmethod
    def _tin_suffix(person: str, number: str, tense: str, voice: str) -> str:
        if tense != "present":
            raise ValueError(f"Unsupported tense: {tense}")
        supported = {
            # Parasmaipada Suffixes
            ("third", "singular", "present", "P"): "ti",
            ("third", "dual", "present", "P"): "taḥ",
            ("third", "plural", "present", "P"): "nti",
            ("second", "singular", "present", "P"): "si",
            ("second", "dual", "present", "P"): "thaḥ",
            ("second", "plural", "present", "P"): "tha",
            ("first", "singular", "present", "P"): "mi",
            ("first", "dual", "present", "P"): "vaḥ",
            ("first", "plural", "present", "P"): "maḥ",
            
            # Atmanepada Suffixes
            ("third", "singular", "present", "A"): "te",
            ("third", "dual", "present", "A"): "ite",
            ("third", "plural", "present", "A"): "nte",
            ("second", "singular", "present", "A"): "se",
            ("second", "dual", "present", "A"): "ithe",
            ("second", "plural", "present", "A"): "dhve",
            ("first", "singular", "present", "A"): "e",
            ("first", "dual", "present", "A"): "vahe",
            ("first", "plural", "present", "A"): "mahe",
        }
        # Default to Parasmaipada if Ubhayapada or missing
        v = "A" if voice == "A" else "P"
        return supported[(person, number, tense, v)]
