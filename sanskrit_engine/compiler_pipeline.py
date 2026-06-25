"""
Object-Oriented Pāṇinian Sanskrit Compiler Pipeline (Prakriyā Flow)
Implements Aṣṭādhyāyī's state-dependent compiler architecture:
- DerivationContext: State manager encapsulating 11D vectors, string state, meta, and flags.
- PaniniRule hierarchy: Abstract base rule and 9 specialized Sūtra Prakāra subclasses.
- RuleFactory: Config parser dynamically instantiating rule configs.
- GrammarEngine: Waterfall execution pipeline prioritizing Apavāda before Utsarga.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Set, Union


class DerivationContext:
    """
    Central State Manager for Pāṇinian derivations.
    Mutates throughout the waterfall execution pipeline.
    """
    def __init__(
        self,
        vector: Union[List[int], Dict[str, Any]],
        base_string: str,
        suffix_string: str = "",
        db_meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        # 1. Input Vector (11D array [V0..V10] or dictionary)
        self.vector = vector
        
        # Helper accessors for vector attributes
        self._vec_list: List[int] = []
        if isinstance(vector, list):
            self._vec_list = list(vector)
            while len(self._vec_list) < 11:
                self._vec_list.append(0)
        elif isinstance(vector, dict):
            # Convert dict vector representation to 11D list
            self._vec_list = [
                vector.get("concept_id", 0),
                vector.get("word_class", 1),
                vector.get("upasarga", 0),
                vector.get("derivative_intent", 0),
                vector.get("compound_role", 0),
                vector.get("lakara", 1),
                vector.get("purusa", 1),
                vector.get("pada", 1),
                vector.get("linga", 1),
                vector.get("vibhakti", 1),
                vector.get("vacana", 1),
            ]
        else:
            self._vec_list = [0] * 11

        # 2. String State (Mutates as rules run) in SLP1 / IAST
        self.stem: str = base_string
        self.vikarana: str = ""
        self.suffix: str = suffix_string

        # 3. Static Lexical Metadata (Loaded from Dhatupatha/Pratipadika DB)
        self.meta: Dict[str, Any] = db_meta or {"gana": "1", "pada": "P", "settva": "S", "is_ajanta": False}

        # 4. Dynamic Pāṇinian Flags (Set by Saṃjñā rules during execution)
        self.flags: Set[str] = set()

        # 5. Compiler Pointers / Meta-logic modes (Set by Paribhāṣā rules)
        self.replacement_mode: str = "DEFAULT"
        self.mocked_state: Optional[str] = None
        self.applied_rules: List[str] = []

    @property
    def pos(self) -> str:
        wc = self._vec_list[1]
        pos_map = {1: "verb", 2: "noun", 3: "adjective", 4: "pronoun", 5: "avyaya", 6: "numeral"}
        return pos_map.get(wc, "verb" if isinstance(self.vector, dict) and self.vector.get("pos") == "verb" else "noun")

    @property
    def tense(self) -> str:
        t = self._vec_list[5]
        tense_map = {1: "present", 2: "past", 3: "future", 4: "imperative", 5: "potential", 6: "perfect"}
        return tense_map.get(t, "present")

    @property
    def person(self) -> str:
        p = self._vec_list[6]
        return {1: "third", 2: "second", 3: "first"}.get(p, "third")

    @property
    def number(self) -> str:
        n = self._vec_list[10]
        return {1: "singular", 2: "dual", 3: "plural"}.get(n, "singular")

    @property
    def voice(self) -> str:
        v = self._vec_list[7]
        return {1: "P", 2: "A", 3: "Passive"}.get(v, self.meta.get("pada", "P"))

    @property
    def gender(self) -> str:
        g = self._vec_list[8]
        return {1: "masculine", 2: "feminine", 3: "neuter"}.get(g, "masculine")

    @property
    def case_idx(self) -> int:
        return self._vec_list[9]

    @property
    def final_string(self) -> str:
        """Returns fully concatenated string smoothed by phonetic junctions."""
        return self.stem + self.vikarana + self.suffix

    def switch_to_noun_pipeline(self) -> None:
        """Recursive loop: allows Kṛdanta verb output to re-enter nominal declension."""
        self._vec_list[1] = 2  # Set word_class = Substantive Noun
        self.flags.add("pratipadika")


class PaniniRule(ABC):
    """Abstract Base Class for all ~4,000 Pāṇinian Sūtras."""
    def __init__(self) -> None:
        self.rule_id: str = "0.0.0"
        self.name: str = "Abstract Sutra"
        self.priority: int = 0  # Higher priority = Apavāda (runs earlier)
        self.category: str = "vidhi"

    @abstractmethod
    def is_applicable(self, context: DerivationContext) -> bool:
        """Returns True if the current context state triggers this rule."""
        pass

    @abstractmethod
    def apply(self, context: DerivationContext) -> None:
        """Mutates the context state object."""
        pass


# --- Sūtra Prakāra (Rule Categories) Subclasses ---

class SamjnaRule(PaniniRule):
    """Assigns technical names / flags (Saṃjñā) to state conditions."""
    def __init__(self, flag_name: str, condition_func: Callable[[DerivationContext], bool], rule_id: str = "1.1.1", priority: int = 200) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.flag_name = flag_name
        self._cond = condition_func
        self.priority = priority
        self.category = "samjna"

    def is_applicable(self, context: DerivationContext) -> bool:
        return self.flag_name not in context.flags and self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        context.flags.add(self.flag_name)
        context.applied_rules.append(f"{self.rule_id} ({self.flag_name}_samjna)")


class ParibhashaRule(PaniniRule):
    """Meta-rules governing compiler pointers and conflict resolution parameters."""
    def __init__(self, mode_name: str, condition_func: Callable[[DerivationContext], bool], rule_id: str = "1.1.52", priority: int = 180) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.mode_name = mode_name
        self._cond = condition_func
        self.priority = priority
        self.category = "paribhasha"

    def is_applicable(self, context: DerivationContext) -> bool:
        return context.replacement_mode != self.mode_name and self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        context.replacement_mode = self.mode_name
        context.applied_rules.append(f"{self.rule_id} ({self.mode_name}_paribhasha)")


class AdhikaraRule(PaniniRule):
    """Header rules setting domain scopes that subsequent rules inherit."""
    def __init__(self, domain_flag: str, condition_func: Callable[[DerivationContext], bool], rule_id: str = "3.1.1", priority: int = 190) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.domain_flag = domain_flag
        self._cond = condition_func
        self.priority = priority
        self.category = "adhikara"

    def is_applicable(self, context: DerivationContext) -> bool:
        return self.domain_flag not in context.flags and self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        context.flags.add(self.domain_flag)
        context.applied_rules.append(f"{self.rule_id} ({self.domain_flag}_adhikara)")


class AtideshaRule(PaniniRule):
    """Extension/mocking rules treating Object A as if it were Object B."""
    def __init__(self, mock_target: str, condition_func: Callable[[DerivationContext], bool], rule_id: str = "1.2.1", priority: int = 150) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.mock_target = mock_target
        self._cond = condition_func
        self.priority = priority
        self.category = "atidesha"

    def is_applicable(self, context: DerivationContext) -> bool:
        return context.mocked_state != self.mock_target and self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        context.mocked_state = self.mock_target
        context.applied_rules.append(f"{self.rule_id} (mock_{self.mock_target})")


class NiyamaRule(PaniniRule):
    """Restriction rules restricting operations when two vidhi rules conflict."""
    def __init__(self, restriction_flag: str, condition_func: Callable[[DerivationContext], bool], rule_id: str = "1.3.1", priority: int = 170) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.restriction_flag = restriction_flag
        self._cond = condition_func
        self.priority = priority
        self.category = "niyama"

    def is_applicable(self, context: DerivationContext) -> bool:
        return self.restriction_flag not in context.flags and self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        context.flags.add(self.restriction_flag)
        context.applied_rules.append(f"{self.rule_id} (niyama_{self.restriction_flag})")


class PratyayaRule(PaniniRule):
    """Fetches and attaches raw Pāṇinian suffixes based on semantic vector intent."""
    def __init__(self, rule_id: str, suffix_val: str, condition_func: Callable[[DerivationContext], bool], priority: int = 100) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.suffix_val = suffix_val
        self._cond = condition_func
        self.priority = priority
        self.category = "pratyaya"

    def is_applicable(self, context: DerivationContext) -> bool:
        return not context.suffix and self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        context.suffix = self.suffix_val
        context.applied_rules.append(f"{self.rule_id} (+{self.suffix_val})")


class AngaKaryaRule(PaniniRule):
    """Modifies stem or vikarana (Guṇa/Vṛddhi, root mutations, class infixes)."""
    def __init__(
        self,
        rule_id: str,
        name: str,
        condition_func: Callable[[DerivationContext], bool],
        mutation_func: Callable[[DerivationContext], None],
        priority: int = 100,
    ) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.name = name
        self._cond = condition_func
        self._mutate = mutation_func
        self.priority = priority
        self.category = "anga_karya"

    def is_applicable(self, context: DerivationContext) -> bool:
        return self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        self._mutate(context)
        context.applied_rules.append(f"{self.rule_id} ({self.name})")


class SandhiRule(PaniniRule):
    """Internal and External morphophonemic string combinations."""
    def __init__(
        self,
        rule_id: str,
        name: str,
        condition_func: Callable[[DerivationContext], bool],
        sandhi_func: Callable[[DerivationContext], None],
        priority: int = 50,
    ) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.name = name
        self._cond = condition_func
        self._sandhi = sandhi_func
        self.priority = priority
        self.category = "sandhi"

    def is_applicable(self, context: DerivationContext) -> bool:
        return self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        self._sandhi(context)
        context.applied_rules.append(f"{self.rule_id} ({self.name})")


class TripadiRule(PaniniRule):
    """Asiddha terminal phonetics executing strictly top-to-bottom without going back."""
    def __init__(
        self,
        rule_id: str,
        name: str,
        condition_func: Callable[[DerivationContext], bool],
        tripadi_func: Callable[[DerivationContext], None],
        priority: int = 10,
    ) -> None:
        super().__init__()
        self.rule_id = rule_id
        self.name = name
        self._cond = condition_func
        self._tripadi = tripadi_func
        self.priority = priority
        self.category = "tripadi"

    def is_applicable(self, context: DerivationContext) -> bool:
        return self._cond(context)

    def apply(self, context: DerivationContext) -> None:
        self._tripadi(context)
        context.applied_rules.append(f"{self.rule_id} ({self.name})")


# --- Concrete Core Workhorse Rules (Built-in Library) ---

class GamToGacchRule(AngaKaryaRule):
    """Apavāda Exception 7.3.77: iṣugamiye... gam -> gacch in non-sārva/present tenses."""
    def __init__(self) -> None:
        super().__init__(
            rule_id="7.3.77",
            name="iṣugamiye... gam_to_gacch",
            condition_func=lambda ctx: ctx.stem == "gam" and ctx.tense in ["present", "imperative", "potential", "past"],
            mutation_func=lambda ctx: setattr(ctx, "stem", "gacch"),
            priority=150,  # Exception runs before general rules
        )


class HanToGhnRule(AngaKaryaRule):
    """Apavāda Exception 7.3.54: ho hante... han -> ghn before vowel-initial weak endings."""
    def __init__(self) -> None:
        super().__init__(
            rule_id="7.3.54",
            name="ho hante... han_to_ghn",
            condition_func=lambda ctx: ctx.stem == "han" and ctx.number == "plural" and ctx.tense == "present",
            mutation_func=lambda ctx: setattr(ctx, "stem", "ghn"),
            priority=150,
        )


class Class1InfixRule(AngaKaryaRule):
    """Utsarga General 3.1.68: kartari śap -> Class 1 active verbs insert infix 'a'."""
    def __init__(self) -> None:
        super().__init__(
            rule_id="3.1.68",
            name="kartari śap",
            condition_func=lambda ctx: ctx.meta.get("gana") == "1" and ctx.voice in ["P", "A"] and not ctx.vikarana and ctx.tense in ["present", "imperative", "potential", "past"],
            mutation_func=lambda ctx: setattr(ctx, "vikarana", "a"),
            priority=100,
        )


class ItAgamaFutureRule(AngaKaryaRule):
    """7.2.35: ārdhadhātukasyeḍ valādeḥ -> seṭ verbs in future tense insert iṭ connecting vowel."""
    def __init__(self) -> None:
        super().__init__(
            rule_id="7.2.35",
            name="iṭ_āgama",
            condition_func=lambda ctx: ctx.tense == "future" and ctx.meta.get("settva") == "S" and not ctx.vikarana,
            mutation_func=lambda ctx: setattr(ctx, "vikarana", "iṣya"),
            priority=120,
        )


class FutureAnitRule(AngaKaryaRule):
    """Future tense infix sya for aniṭ verbs."""
    def __init__(self) -> None:
        super().__init__(
            rule_id="3.1.33",
            name="sya_future",
            condition_func=lambda ctx: ctx.tense == "future" and ctx.meta.get("settva") != "S" and not ctx.vikarana,
            mutation_func=lambda ctx: setattr(ctx, "vikarana", "sya"),
            priority=110,
        )


class BhuGunaRule(AngaKaryaRule):
    """7.3.84: sārvadhātukārthadhātukayoḥ -> Guṇa vowel strengthening on stem ending in i/u/ṛ."""
    def __init__(self) -> None:
        def _cond(ctx: DerivationContext) -> bool:
            return bool(ctx.stem.endswith("ū") or ctx.stem.endswith("u") or ctx.stem.endswith("i") or ctx.stem.endswith("ī")) and bool(ctx.vikarana.startswith("a") or ctx.vikarana.startswith("e"))
        def _mutate(ctx: DerivationContext) -> None:
            if ctx.stem.endswith("ū") or ctx.stem.endswith("u"):
                ctx.stem = ctx.stem[:-1] + "o"
            elif ctx.stem.endswith("ī") or ctx.stem.endswith("i"):
                ctx.stem = ctx.stem[:-1] + "e"
        super().__init__(rule_id="7.3.84", name="sarvadhatuka_guna", condition_func=_cond, mutation_func=_mutate, priority=90)


class AtoGuneSandhiRule(SandhiRule):
    """6.1.97: ato guṇe -> a + a -> a (or a + e -> e) boundary merging."""
    def __init__(self) -> None:
        def _cond(ctx: DerivationContext) -> bool:
            return ctx.vikarana.endswith("a") and ctx.suffix.startswith("a")
        def _sandhi(ctx: DerivationContext) -> None:
            ctx.suffix = ctx.suffix[1:]  # Merge short 'a' of suffix with 'a' of vikarana
        super().__init__(rule_id="6.1.97", name="ato guṇe", condition_func=_cond, sandhi_func=_sandhi, priority=60)


class BhavaSandhiRule(SandhiRule):
    """6.1.78: eco 'yavāyāvaḥ -> o + a -> ava."""
    def __init__(self) -> None:
        def _cond(ctx: DerivationContext) -> bool:
            return ctx.stem.endswith("o") and (ctx.vikarana.startswith("a") or ctx.suffix.startswith("a"))
        def _sandhi(ctx: DerivationContext) -> None:
            ctx.stem = ctx.stem[:-1] + "av"
        super().__init__(rule_id="6.1.78", name="eco yavāyāvaḥ", condition_func=_cond, sandhi_func=_sandhi, priority=65)


# --- RuleFactory & Config Parser ---

class RuleFactory:
    """Instantiates concrete PaniniRule subclasses from dict/JSON configurations."""
    @staticmethod
    def create_rule(config: Dict[str, Any]) -> PaniniRule:
        cat = config.get("category", "vidhi").lower()
        r_id = config.get("rule_id", "0.0.0")
        name = config.get("name", "Custom Rule")
        prio = config.get("priority", 100)

        exec_str = config.get("operation", {}).get("executable", "lambda token, env: token")
        
        class DynamicRule(AngaKaryaRule):
            def __init__(self) -> None:
                super().__init__(
                    rule_id=r_id,
                    name=name,
                    condition_func=lambda ctx: True if not config.get("domain") or ctx.pos in config.get("domain", []) else False,
                    mutation_func=lambda ctx: setattr(ctx, "stem", str(eval(exec_str)({"text": ctx.stem, "pos": ctx.pos}, {"root": ctx.stem, "tense": ctx.tense}).get("text", ctx.stem)) if isinstance(eval(exec_str)({"text": ctx.stem, "pos": ctx.pos}, {"root": ctx.stem, "tense": ctx.tense}), dict) else ctx.stem),
                    priority=prio,
                )
        return DynamicRule()


# --- GrammarEngine (Prakriyā Pipeline) ---

class GrammarEngine:
    """
    Cascading Waterfall Execution Pipeline.
    Passes DerivationContext through strict mathematical derivation phases.
    """
    def __init__(self, custom_rules: Optional[List[PaniniRule]] = None) -> None:
        self.samjna_rules: List[SamjnaRule] = [
            SamjnaRule("ghi", lambda ctx: ctx.stem.endswith("i") or ctx.stem.endswith("u"), "1.4.7"),
            SamjnaRule("nadi", lambda ctx: ctx.stem.endswith("ī") or ctx.stem.endswith("ū"), "1.4.3"),
        ]
        self.paribhasha_rules: List[ParibhashaRule] = [
            ParibhashaRule("LAST_CHAR_ONLY", lambda ctx: True, "1.1.52"),
        ]
        self.adhikara_rules: List[AdhikaraRule] = []
        self.atidesha_rules: List[AtideshaRule] = []
        self.niyama_rules: List[NiyamaRule] = []

        self.special_stem_rules: List[AngaKaryaRule] = [GamToGacchRule(), HanToGhnRule()]
        self.vikarana_rules: List[AngaKaryaRule] = [ItAgamaFutureRule(), FutureAnitRule(), Class1InfixRule()]
        self.guna_vriddhi_rules: List[AngaKaryaRule] = [BhuGunaRule()]
        self.internal_sandhi_rules: List[SandhiRule] = [BhavaSandhiRule(), AtoGuneSandhiRule()]
        self.tripadi_rules: List[TripadiRule] = []

        if custom_rules:
            for r in custom_rules:
                if isinstance(r, SamjnaRule): self.samjna_rules.append(r)
                elif isinstance(r, ParibhashaRule): self.paribhasha_rules.append(r)
                elif isinstance(r, SandhiRule): self.internal_sandhi_rules.append(r)
                elif isinstance(r, TripadiRule): self.tripadi_rules.append(r)
                elif isinstance(r, AngaKaryaRule):
                    if r.priority >= 150: self.special_stem_rules.append(r)
                    else: self.vikarana_rules.append(r)

        self.special_stem_rules.sort(key=lambda x: x.priority, reverse=True)
        self.vikarana_rules.sort(key=lambda x: x.priority, reverse=True)
        self.guna_vriddhi_rules.sort(key=lambda x: x.priority, reverse=True)
        self.internal_sandhi_rules.sort(key=lambda x: x.priority, reverse=True)

        self.pipeline: List[Callable[[DerivationContext], None]] = [
            self._apply_samjnas,
            self._apply_paribhashas,
            self._apply_special_stems,
            self._apply_pratyayas,
            self._apply_vikaranas,
            self._apply_guna_vriddhi,
            self._apply_internal_sandhi,
            self._apply_tripadi,
        ]

    def generate(
        self,
        vector: Union[List[int], Dict[str, Any]],
        db_meta: Dict[str, Any],
        base_string: str,
        raw_suffix: str = "",
    ) -> str:
        """Executes waterfall derivation pipeline on input coordinates."""
        ctx = DerivationContext(vector, base_string, raw_suffix, db_meta)
        for phase_fn in self.pipeline:
            phase_fn(ctx)
        return ctx.final_string

    def _apply_samjnas(self, ctx: DerivationContext) -> None:
        for r in self.samjna_rules:
            if r.is_applicable(ctx): r.apply(ctx)

    def _apply_paribhashas(self, ctx: DerivationContext) -> None:
        for r in self.paribhasha_rules:
            if r.is_applicable(ctx): r.apply(ctx)

    def _apply_special_stems(self, ctx: DerivationContext) -> None:
        for r in self.special_stem_rules:
            if r.is_applicable(ctx):
                r.apply(ctx)
                break  # Exception breaks loop!

    def _apply_pratyayas(self, ctx: DerivationContext) -> None:
        if not ctx.suffix and ctx.pos == "verb":
            endings = {
                ("third", "singular", "present", "P"): "ti",
                ("third", "plural", "present", "P"): "anti",
                ("first", "singular", "present", "P"): "mi",
                ("second", "singular", "present", "P"): "si",
                ("third", "singular", "future", "P"): "ti",
                ("third", "plural", "future", "P"): "anti",
                ("first", "singular", "future", "P"): "mi",
            }
            ctx.suffix = endings.get((ctx.person, ctx.number, ctx.tense, ctx.voice), "ti")

    def _apply_vikaranas(self, ctx: DerivationContext) -> None:
        for r in self.vikarana_rules:
            if r.is_applicable(ctx):
                r.apply(ctx)
                break

    def _apply_guna_vriddhi(self, ctx: DerivationContext) -> None:
        for r in self.guna_vriddhi_rules:
            if r.is_applicable(ctx):
                r.apply(ctx)
                break

    def _apply_internal_sandhi(self, ctx: DerivationContext) -> None:
        for r in self.internal_sandhi_rules:
            if r.is_applicable(ctx):
                r.apply(ctx)

    def _apply_tripadi(self, ctx: DerivationContext) -> None:
        for r in self.tripadi_rules:
            if r.is_applicable(ctx):
                r.apply(ctx)
