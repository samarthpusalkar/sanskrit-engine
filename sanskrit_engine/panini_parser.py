"""
Complete Pāṇini Rule Parser
Parses all ~4,000 Sūtras from ashtadhyayi_raw.json and ashtadhyayi_db.json.
Converts traditional grammatical records (PadacCheda, Anuvṛtti, Adhikāra) into
deterministic Object-Oriented PaniniRule instances.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .pratyahara import PratyaharaResolver
from .compiler_pipeline import (
    AdhikaraRule,
    AngaKaryaRule,
    AtideshaRule,
    DerivationContext,
    NiyamaRule,
    PaniniRule,
    ParibhashaRule,
    SamjnaRule,
    SandhiRule,
)


class CaseCompiler:
    """Compiles Pāṇinian noun cases (vibhakti) from PadacCheda into declarative IR AST conditions."""
    def __init__(self, pratyahara_resolver: Optional[PratyaharaResolver] = None) -> None:
        self.resolver = pratyahara_resolver or PratyaharaResolver()

    def _clean_anubandhas(self, text: str) -> Tuple[str, Dict[str, bool]]:
        flags = {
            "is_sit": False,
            "is_ngit": False,
            "is_kit": False,
            "is_tit": False,
        }
        clean_text = text
        if text.startswith("ś") or text.endswith("ś"):
            flags["is_sit"] = True
            clean_text = clean_text.strip("ś")
        if text.startswith("ṅ") or text.endswith("ṅ"):
            flags["is_ngit"] = True
            clean_text = clean_text.strip("ṅ")
        if text.startswith("k") or text.endswith("k"):
            flags["is_kit"] = True
            clean_text = clean_text.strip("k")
        if text.startswith("ṭ") or text.endswith("ṭ"):
            flags["is_tit"] = True
            clean_text = clean_text.strip("ṭ")
        return clean_text, flags

    def compile_rule_to_ir(self, sutra_id: str, padaccheda: List[Dict[str, Any]], sutra_type: List[str], domain: str = "general") -> Dict[str, Any]:
        conditions: Dict[str, Any] = {}
        operations: Dict[str, Any] = {}
        meta_flags: Dict[str, bool] = {}

        target_terms = []
        left_terms = []
        right_terms = []
        result_terms = []

        for item in padaccheda:
            pada = item.get("pada", "").strip()
            vib = item.get("vibhakti", 0)

            clean_pada, flags = self._clean_anubandhas(pada)
            for k, v in flags.items():
                if v: meta_flags[k] = True

            stem = item.get("pada_split", clean_pada).split("-")[0]
            if stem.lower() in {"ik", "ac", "yaṇ", "hal", "al", "iṇ"}:
                decoded = self.resolver.decode(stem.lower())
            else:
                decoded = []

            terms = decoded if decoded else [clean_pada]

            if vib == 6:
                target_terms.extend(terms)
            elif vib == 5:
                left_terms.extend(terms)
            elif vib == 7:
                right_terms.extend(terms)
            elif vib == 1:
                result_terms.extend(terms)

        if target_terms:
            conditions["target_regex"] = "[" + ", ".join(target_terms) + "]"
        if left_terms:
            conditions["lookbehind_regex"] = "[" + ", ".join(left_terms) + "]"
        if right_terms:
            conditions["lookahead_regex"] = "[" + ", ".join(right_terms) + "]"
        if result_terms:
            operations["substitute"] = result_terms

        return {
            "rule_id": sutra_id,
            "rule_type": sutra_type[0] if sutra_type else "विधि",
            "domain": domain,
            "conditions": conditions,
            "operations": operations,
            "metadata": meta_flags,
        }


class AnuvrttiResolver:
    """Scans sūtras sequentially, carrying forward active Adhikāra domains and Anuvṛtti terms."""
    def __init__(self) -> None:
        self.active_domain = "general"

    def process_sutra(self, raw_sutra: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        s_type = raw_sutra.get("Sutra_type", [])
        term = raw_sutra.get("Term", "")
        if any("अधिकार" in st for st in s_type):
            if "अङ्ग" in term or "anga" in term.lower():
                self.active_domain = "anga"
            elif "प्रत्यय" in term or "pratyaya" in term.lower():
                self.active_domain = "pratyaya"
            elif "सन्धि" in term or "sandhi" in term.lower():
                self.active_domain = "sandhi"

        padaccheda = list(raw_sutra.get("PadacCheda", []))
        return self.active_domain, padaccheda


class PaniniCorpusParser:
    """
    Parses full Aṣṭādhyāyī JSON databases and hydrates executable rule classes.
    """
    def __init__(self, raw_path: Optional[Union[str, Path]] = None, db_path: Optional[Union[str, Path]] = None) -> None:
        self.raw_path = Path(raw_path) if raw_path else Path("data/ashtadhyayi_raw.json")
        self.db_path = Path(db_path) if db_path else Path("data/ashtadhyayi_db.json")
        self.parsed_rules: List[PaniniRule] = []

    def load_and_parse(self) -> List[PaniniRule]:
        """Loads raw sutras and compiled operations, returning executable pipeline rules."""
        rules: List[PaniniRule] = []
        
        # 1. Load compiled operations from ashtadhyayi_db.json if available
        compiled_ops: Dict[str, Dict[str, Any]] = {}
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                db_data = json.load(f)
                for r_record in db_data.get("rules", []):
                    r_id = r_record.get("rule_id")
                    if r_id: compiled_ops[r_id] = r_record

        # 2. Parse traditional grammar details from ashtadhyayi_raw.json
        if self.raw_path.exists():
            with open(self.raw_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                sutras_dict = raw_data.get("sutras", {})
                for s_key, s_data in sutras_dict.items():
                    rule_obj = self._parse_single_sutra(s_data, compiled_ops.get(s_data.get("Sutra_id", "")))
                    if rule_obj:
                        rules.append(rule_obj)
        else:
            # Fallback if raw devanagari db is not locally mounted: load from db_data
            for r_id, r_record in compiled_ops.items():
                rules.append(self._create_rule_from_compiled(r_record))

        self.parsed_rules = rules
        return rules

    def compile_to_ir(self) -> List[Dict[str, Any]]:
        """Compiles raw linguistic JSON into declarative AST Intermediate Representation."""
        ir_list: List[Dict[str, Any]] = []
        if not self.raw_path.exists():
            return ir_list

        case_compiler = CaseCompiler()
        anuvrtti_resolver = AnuvrttiResolver()

        with open(self.raw_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            sutras_dict = raw_data.get("sutras", {})
            for s_key, s_data in sutras_dict.items():
                s_id = s_data.get("Sutra_id", "0.0.0")
                s_type = s_data.get("Sutra_type", ["विधि"])
                domain, padaccheda = anuvrtti_resolver.process_sutra(s_data)
                ir_record = case_compiler.compile_rule_to_ir(s_id, padaccheda, s_type, domain)
                ir_list.append(ir_record)
        return ir_list

    def _parse_single_sutra(self, raw_sutra: Dict[str, Any], compiled_rec: Optional[Dict[str, Any]]) -> Optional[PaniniRule]:
        s_id = raw_sutra.get("Sutra_id", "0.0.0")
        s_types = raw_sutra.get("Sutra_type", ["विधि"])
        s_text = raw_sutra.get("Sutra_text", "")
        term = raw_sutra.get("Term", "")

        # Categorize Sūtra Prakāra
        cat = "vidhi"
        for st in s_types:
            if "संज्ञा" in st: cat = "samjna"
            elif "परिभाषा" in st: cat = "paribhasha"
            elif "अधिकार" in st: cat = "adhikara"
            elif "अतिदेश" in st: cat = "atidesha"
            elif "नियम" in st: cat = "niyama"

        priority = 100
        if compiled_rec:
            priority = compiled_rec.get("priority", 100)

        # Transliterate Devanagari Sūtra term to IAST if needed
        term_iast = term
        try:
            from indic_transliteration import sanscript
            if term:
                term_iast = sanscript.transliterate(term, sanscript.DEVANAGARI, sanscript.IAST)
        except ImportError:
            pass

        # Instantiate concrete PaniniRule subclass
        if cat == "samjna":
            return SamjnaRule(
                flag_name=term_iast or f"samjna_{s_id}",
                condition_func=lambda ctx: True if compiled_rec else False,
                rule_id=s_id,
                priority=priority,
            )
        elif cat == "paribhasha":
            return ParibhashaRule(
                mode_name=term_iast or f"paribhasha_{s_id}",
                condition_func=lambda ctx: True,
                rule_id=s_id,
                priority=priority,
            )
        elif cat == "adhikara":
            return AdhikaraRule(
                domain_flag=term_iast or f"adhikara_{s_id}",
                condition_func=lambda ctx: True,
                rule_id=s_id,
                priority=priority,
            )
        elif cat == "atidesha":
            return AtideshaRule(
                mock_target=term_iast or f"atidesha_{s_id}",
                condition_func=lambda ctx: True,
                rule_id=s_id,
                priority=priority,
            )
        elif cat == "niyama":
            return NiyamaRule(
                restriction_flag=term_iast or f"niyama_{s_id}",
                condition_func=lambda ctx: True,
                rule_id=s_id,
                priority=priority,
            )
        else:
            # Vidhi / AngaKarya / Sandhi rule
            if compiled_rec and "executable" in compiled_rec.get("operation", {}):
                exec_str = compiled_rec["operation"]["executable"]
                return AngaKaryaRule(
                    rule_id=s_id,
                    name=compiled_rec.get("name", s_text),
                    condition_func=lambda ctx: True if ctx.pos in compiled_rec.get("domain", ["verb", "noun"]) else False,
                    mutation_func=lambda ctx: setattr(ctx, "stem", str(eval(exec_str)({"text": ctx.stem, "pos": ctx.pos}, {"root": ctx.stem, "tense": ctx.tense}).get("text", ctx.stem)) if isinstance(eval(exec_str)({"text": ctx.stem, "pos": ctx.pos}, {"root": ctx.stem, "tense": ctx.tense}), dict) else ctx.stem),
                    priority=priority,
                )
            else:
                return AngaKaryaRule(
                    rule_id=s_id,
                    name=s_text or f"vidhi_{s_id}",
                    condition_func=lambda ctx: False, # Stub until compiled
                    mutation_func=lambda ctx: None,
                    priority=priority,
                )

    def _create_rule_from_compiled(self, rec: Dict[str, Any]) -> PaniniRule:
        r_id = rec.get("rule_id", "0.0.0")
        name = rec.get("name", "Compiled Rule")
        prio = rec.get("priority", 100)
        dom = rec.get("domain", ["verb", "noun"])
        return AngaKaryaRule(
            rule_id=r_id,
            name=name,
            condition_func=lambda ctx: ctx.pos in dom,
            mutation_func=lambda ctx: None,
            priority=prio,
        )


def parse_all_ashtadhyayi_rules(raw_path: str = "data/ashtadhyayi_raw.json", db_path: str = "data/ashtadhyayi_db.json") -> List[PaniniRule]:
    """Convenience helper function parsing entire Pāṇinian corpus."""
    parser = PaniniCorpusParser(raw_path, db_path)
    return parser.load_and_parse()
