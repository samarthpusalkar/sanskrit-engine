"""
Quarantined Legacy v1 Prototype Classes.
Contains deprecated Western hardcoded lookup tables (_sup_suffix, _tin_suffix)
and heuristic template declensions.
DEPRECATED: Do not use in active production pipeline. Use GenerativePaniniMorphology instead.
"""

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
    """Explicit v0 morphology templates. DEPRECATED."""
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

    def derive(self, root: str, derivation_type: str) -> str:
        return root


class RuleBasedMorphology:
    """Legacy v1 hardcoded morphology. DEPRECATED."""
    def __init__(self, rules: list[Rule]) -> None:
        self.engine = Engine(rules)

    def derive(self, root: str, derivation_type: str) -> str:
        if derivation_type == "none" or not derivation_type:
            return root
        vrddhi_map = {'a': 'ā', 'i': 'ai', 'ī': 'ai', 'u': 'au', 'ū': 'au', 'ṛ': 'ār', 'ṝ': 'ār'}
        guna_map = {'i': 'e', 'ī': 'e', 'u': 'o', 'ū': 'o', 'ṛ': 'ar', 'ṝ': 'ar'}
        def apply_mutation(r: str, mutation_map: dict) -> str:
            for i, char in enumerate(r):
                if char in mutation_map:
                    return r[:i] + mutation_map[char] + r[i+1:]
            return r
        if derivation_type == "ghañ":
            stem = apply_mutation(root, vrddhi_map)
            if stem.endswith('au'): stem = stem[:-2] + 'āv'
            elif stem.endswith('ai'): stem = stem[:-2] + 'āy'
            return stem + 'a'
        elif derivation_type == "lyuṭ":
            stem = apply_mutation(root, guna_map)
            if stem.endswith('o'): stem = stem[:-1] + 'av'
            elif stem.endswith('e'): stem = stem[:-1] + 'ay'
            return stem + 'ana'
        elif derivation_type == "ktvā":
            stem = root
            if stem.endswith('m') or stem.endswith('n'): stem = stem[:-1]
            return stem + 'tvā'
        elif derivation_type == "tumun":
            stem = apply_mutation(root, guna_map)
            if stem.endswith('m'): stem = stem[:-1] + 'n'
            return stem + 'tum'
        return root

    def decline(self, noun: NounEntry, case: str, number: str) -> GeneratedForm:
        suffix = self._sup_suffix(noun.gender, case, number)
        tokens = [
            Token(noun.stem, tags={"stem"}, features={"pos": "noun", "gender": noun.gender, "stem_final": noun.stem[-1]}),
            Token(suffix, tags={"sup"}, features={"case": case, "number": number}),
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(result.text, noun.stem, {"pos": "noun", "gender": noun.gender, "case": case, "number": number}, tuple(step.rule_id for step in result.trace))

    def conjugate(self, verb: VerbEntry, person: str, number: str, tense: str, voice: str = "P", settva: str = "S") -> GeneratedForm:
        suffix = self._tin_suffix(person, number, tense, voice, settva)
        tokens = [
            Token(verb.present_stem, tags={"verb_stem"}, features={"pos": "verb", "root": verb.root}),
            Token(suffix, tags={"tin"}, features={"person": person, "number": number, "tense": tense, "voice": voice}),
        ]
        result = self.engine.process(tokens)
        return GeneratedForm(result.text, verb.root, {"pos": "verb", "person": person, "number": number, "tense": tense, "voice": voice}, tuple(step.rule_id for step in result.trace))

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
            ("masculine", "genitive", "plural"): "ām",
            ("neuter", "nominative", "singular"): "su",
            ("neuter", "accusative", "singular"): "am",
            ("neuter", "instrumental", "singular"): "ṭā",
            ("neuter", "dative", "singular"): "ṅe",
            ("neuter", "genitive", "singular"): "ṅas",
            ("neuter", "locative", "singular"): "ṅi",
            ("neuter", "nominative", "plural"): "jas",
            ("neuter", "accusative", "plural"): "śas",
            ("neuter", "genitive", "plural"): "ām",
            ("feminine", "nominative", "singular"): "su",
            ("feminine", "accusative", "singular"): "am",
            ("feminine", "instrumental", "singular"): "ṭā",
            ("feminine", "dative", "singular"): "ṅe",
            ("feminine", "genitive", "singular"): "ṅas",
            ("feminine", "locative", "singular"): "ṅi",
            ("feminine", "nominative", "plural"): "jas",
            ("feminine", "accusative", "plural"): "śas",
            ("feminine", "genitive", "plural"): "ām",
        }
        return supported.get((gender, case, number), "su")

    @staticmethod
    def _tin_suffix(person: str, number: str, tense: str, voice: str, settva: str) -> str:
        if tense not in ["present", "future"]: raise ValueError(f"Unsupported tense: {tense}")
        supported = {
            ("third", "singular", "present", "P"): "tip",
            ("third", "dual", "present", "P"): "taḥ",
            ("third", "plural", "present", "P"): "jhi",
            ("second", "singular", "present", "P"): "sip",
            ("second", "dual", "present", "P"): "thaḥ",
            ("second", "plural", "present", "P"): "tha",
            ("first", "singular", "present", "P"): "mip",
            ("first", "dual", "present", "P"): "vaḥ",
            ("first", "plural", "present", "P"): "maḥ",
            ("third", "singular", "present", "A"): "te",
            ("third", "dual", "present", "A"): "ite",
            ("third", "plural", "present", "A"): "nte",
            ("second", "singular", "present", "A"): "se",
            ("second", "dual", "present", "A"): "ithe",
            ("second", "plural", "present", "A"): "dhve",
            ("first", "singular", "present", "A"): "e",
            ("first", "dual", "present", "A"): "vahe",
            ("first", "plural", "present", "A"): "mahe",
            ("third", "singular", "future", "P"): "syati",
            ("third", "dual", "future", "P"): "syataḥ",
            ("third", "plural", "future", "P"): "syanti",
            ("second", "singular", "future", "P"): "syasi",
            ("second", "dual", "future", "P"): "syathaḥ",
            ("second", "plural", "future", "P"): "syatha",
            ("first", "singular", "future", "P"): "syāmi",
            ("first", "dual", "future", "P"): "syāvaḥ",
            ("first", "plural", "future", "P"): "syāmaḥ",
            ("third", "singular", "future", "A"): "syate",
            ("third", "dual", "future", "A"): "syete",
            ("third", "plural", "future", "A"): "syante",
            ("second", "singular", "future", "A"): "syase",
            ("second", "dual", "future", "A"): "syethe",
            ("second", "plural", "future", "A"): "syadhve",
            ("first", "singular", "future", "A"): "sye",
            ("first", "dual", "future", "A"): "syāvahe",
            ("first", "plural", "future", "A"): "syāmahe",
        }
        v = "A" if voice == "A" else "P"
        suffix = supported.get((person, number, tense, v), "")
        if tense == "future" and settva == "S": suffix = "i" + suffix
        return suffix
