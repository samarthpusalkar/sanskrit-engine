from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

from .lexicon import DEFAULT_NOUNS, DEFAULT_VERBS, NounEntry, VerbEntry
from .morphology import GeneratedForm, TemplateMorphology


@dataclass(frozen=True)
class SentenceSpec:
    subject: NounEntry
    verb: VerbEntry
    object: NounEntry | None = None


@dataclass(frozen=True)
class GeneratedSentence:
    text: str
    gloss: str
    forms: tuple[GeneratedForm, ...]
    rule_ids: tuple[str, ...]


class SanskritGenerator:
    def __init__(
        self,
        nouns: Iterable[NounEntry] = DEFAULT_NOUNS,
        verbs: Iterable[VerbEntry] = DEFAULT_VERBS,
        morphology: TemplateMorphology | None = None,
        seed: int = 0,
    ) -> None:
        self.nouns = tuple(nouns)
        self.verbs = tuple(verbs)
        self.morphology = morphology or TemplateMorphology()
        self.random = random.Random(seed)

    def generate(self, spec: SentenceSpec) -> GeneratedSentence:
        subject = self.morphology.decline(spec.subject, "nominative", "singular")
        verb = self.morphology.conjugate(spec.verb, "third", "singular", "present")
        forms = [subject]
        gloss_parts = [spec.subject.gloss]
        if spec.object is not None:
            obj = self.morphology.decline(spec.object, "accusative", "singular")
            forms.append(obj)
            gloss_parts.append(spec.object.gloss)
        forms.append(verb)
        gloss_parts.append(spec.verb.gloss)
        return GeneratedSentence(
            text=" ".join(form.text for form in forms),
            gloss=" ".join(gloss_parts),
            forms=tuple(forms),
            rule_ids=tuple(rule_id for form in forms for rule_id in form.rule_ids),
        )

    def generate_many(self, count: int) -> list[GeneratedSentence]:
        sentences: list[GeneratedSentence] = []
        subjects = [noun for noun in self.nouns if noun.gender == "masculine"]
        for _ in range(count):
            subject = self.random.choice(subjects)
            verb = self.random.choice(self.verbs)
            obj = self.random.choice(self.nouns) if verb.root in {"paṭh", "khād"} else None
            sentences.append(self.generate(SentenceSpec(subject, verb, obj)))
        return sentences

