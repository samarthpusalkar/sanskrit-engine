from __future__ import annotations
import os
from typing import List, Dict, Any, Union, Optional
from .morphology import RuleBasedMorphology
from .lexicon import NounEntry, VerbEntry
from .parser import SanskritParser
from .config_index import *
from .rule_database import RuleDatabase
from .tinganta_db import TingantaDB


class TensorDelta:
    """Represents a surgical modification matrix (delta) for a TensorCoordinate."""
    def __init__(self, vector: List[int]):
        self.vector = vector


class TensorCoordinate:
    """
    Represents a multi-dimensional morphological integer vector.
    Supports 5D (Legacy), 7D (Intermediate), and 11D (Formal Semantic Contract).
    """
    def __init__(self, vector: List[int]):
        self.vector = list(vector)

    def to_11d(self) -> TensorCoordinate:
        vec = self.vector
        if len(vec) == 11: return self
        elif len(vec) == 5:
            root, pos, f1, f2, f3 = vec
            if pos == POS_VOCAB.get("verb", 2):
                return TensorCoordinate([root, pos, 0, 0, 0, f1, f2, 1, 1, 1, f3])
            else:
                return TensorCoordinate([root, pos, 0, 0, 0, 1, 1, 1, f1, f2, f3])
        elif len(vec) == 7:
            up, root, der, pos, f1, f2, f3 = vec
            if pos == POS_VOCAB.get("verb", 2):
                return TensorCoordinate([root, pos, up, der, 0, f1, f2, 1, 1, 1, f3])
            else:
                return TensorCoordinate([root, pos, up, der, 0, 1, 1, 1, f1, f2, f3])
        return TensorCoordinate(vec + [0]*(11 - len(vec)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TensorCoordinate):
            return False
        return self.vector == other.vector

    def __add__(self, delta: TensorDelta) -> TensorCoordinate:
        """Allows surgical mathematical transformations: vector + delta = new_vector"""
        if not isinstance(delta, TensorDelta):
            raise TypeError("Can only add a TensorDelta to a TensorCoordinate.")
        if len(self.vector) != len(delta.vector):
            raise ValueError(f"Vector ({len(self.vector)}D) and Delta ({len(delta.vector)}D) must have the same dimensions.")
        new_vec = [v + d for v, d in zip(self.vector, delta.vector)]
        return TensorCoordinate(new_vec)
        
    def __sub__(self, delta: TensorDelta) -> TensorCoordinate:
        if not isinstance(delta, TensorDelta):
            raise TypeError("Can only subtract a TensorDelta from a TensorCoordinate.")
        if len(self.vector) != len(delta.vector):
            raise ValueError(f"Vector ({len(self.vector)}D) and Delta ({len(delta.vector)}D) must have the same dimensions.")
        new_vec = [v - d for v, d in zip(self.vector, delta.vector)]
        return TensorCoordinate(new_vec)

    def __repr__(self) -> str:
        return f"TensorCoordinate({self.vector})"


class TensorTokenizer:
    """Encodes Sanskrit words into integer tensors and decodes them back dynamically."""
    
    def __init__(self, morphology: RuleBasedMorphology, rule_db: Optional[RuleDatabase] = None, default_dim: int = 5):
        self.morphology = morphology
        self.parser = SanskritParser()
        self.rule_db = rule_db
        self.default_dim = default_dim
        self.stem_map: Dict[str, int] = {}
        self.tinganta_db = TingantaDB()
        self._build_stem_map()
        
    def _build_stem_map(self) -> None:
        """
        Builds a fast reverse Stem Map mapping base stems back to Root IDs.
        Accelerated O(N) indexing without calling slow engine decoding per entry.
        """
        self.stem_map = {}
        for root_str, root_id in ROOT_VOCAB.items():
            self.stem_map[root_str] = root_id
            if root_str.endswith(("a", "i", "u", "ā", "ī", "ū")):
                if len(root_str[:-1]) > 1:
                    self.stem_map[root_str[:-1]] = root_id
            else:
                self.stem_map[root_str + "a"] = root_id
                self.stem_map[root_str + "i"] = root_id
                
        # Add special irregular verb present stems and common irregularities
        stem_exceptions = {
            "gam": "gaccha", "paś": "paśya", "sad": "sīda", "sthā": "tiṣṭha", 
            "mnā": "mana", "dā": "dadā", "han": "han", "sidh": "sidhy", "praviś": "praviś"
        }
        for root, ex_stem in stem_exceptions.items():
            rid = ROOT_VOCAB.get(root)
            if rid:
                self.stem_map[ex_stem] = rid
                if ex_stem.endswith("a") and len(ex_stem) > 1:
                    self.stem_map[ex_stem[:-1]] = rid

    def encode(self, text: str, allow_oov: bool = True) -> List[TensorCoordinate]:
        """
        Parses text and encodes into integer TensorCoordinates.
        """
        tensors = []
        words = text.split()
        
        suffix_map_verb = {
            "anti": (PERSON_VOCAB["third"], NUMBER_VOCAB["plural"]),
            "ante": (PERSON_VOCAB["third"], NUMBER_VOCAB["plural"]),
            "ti": (PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]),
            "te": (PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]),
            "si": (PERSON_VOCAB["second"], NUMBER_VOCAB["singular"]),
            "se": (PERSON_VOCAB["second"], NUMBER_VOCAB["singular"]),
            "mi": (PERSON_VOCAB["first"], NUMBER_VOCAB["singular"]),
            "maḥ": (PERSON_VOCAB["first"], NUMBER_VOCAB["plural"]),
        }
        suffix_map_noun = {
            "asya": (CASE_VOCAB["genitive"], NUMBER_VOCAB["singular"]),
            "sya": (CASE_VOCAB["genitive"], NUMBER_VOCAB["singular"]),
            "am": (CASE_VOCAB["accusative"], NUMBER_VOCAB["singular"]),
            "m": (CASE_VOCAB["accusative"], NUMBER_VOCAB["singular"]),
            "ṃ": (CASE_VOCAB["accusative"], NUMBER_VOCAB["singular"]),
            "ḥ": (CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]),
            "h": (CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]),
            "ena": (CASE_VOCAB["instrumental"], NUMBER_VOCAB["singular"]),
            "āya": (CASE_VOCAB["dative"], NUMBER_VOCAB["singular"]),
            "āt": (CASE_VOCAB["ablative"], NUMBER_VOCAB["singular"]),
            "ād": (CASE_VOCAB["ablative"], NUMBER_VOCAB["singular"]),
            "e": (CASE_VOCAB["locative"], NUMBER_VOCAB["singular"]),
            "au": (CASE_VOCAB["nominative"], NUMBER_VOCAB["dual"]),
            "ābhyām": (CASE_VOCAB["instrumental"], NUMBER_VOCAB["dual"]),
            "ayoḥ": (CASE_VOCAB["genitive"], NUMBER_VOCAB["dual"]),
            "āḥ": (CASE_VOCAB["nominative"], NUMBER_VOCAB["plural"]),
            "aiḥ": (CASE_VOCAB["instrumental"], NUMBER_VOCAB["plural"]),
            "ebhyaḥ": (CASE_VOCAB["dative"], NUMBER_VOCAB["plural"]),
            "ānām": (CASE_VOCAB["genitive"], NUMBER_VOCAB["plural"]),
            "ānāṃ": (CASE_VOCAB["genitive"], NUMBER_VOCAB["plural"]),
            "āṇām": (CASE_VOCAB["genitive"], NUMBER_VOCAB["plural"]),
            "āṇāṃ": (CASE_VOCAB["genitive"], NUMBER_VOCAB["plural"]),
            "āni": (CASE_VOCAB["nominative"], NUMBER_VOCAB["plural"]),
            "āṇi": (CASE_VOCAB["nominative"], NUMBER_VOCAB["plural"]),
            "eṣu": (CASE_VOCAB["locative"], NUMBER_VOCAB["plural"]),
            "ā": (CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]),
        }
        upasargas = ("pra", "parā", "apa", "sam", "anu", "ava", "nis", "nir", "dus", "dur", "vi", "ā", "ni", "adhi", "api", "ati", "su", "ut", "abhi", "prati", "pari", "upa")
        
        for word in words:
            tensor = None
            
            # Step 0: Direct tiṅanta.db lookup (covers ALL lakāras including Liṭ, Laṅ, Luṅ)
            verb_hit = self.tinganta_db.lookup_verb_form(word)
            if verb_hit:
                cid = verb_hit['concept_id']
                if self.default_dim == 5:
                    tensor = [cid, POS_VOCAB['verb'], verb_hit['lakara'], verb_hit['purusa'], verb_hit['vacana']]
                elif self.default_dim == 7:
                    tensor = [0, cid, 0, POS_VOCAB['verb'], verb_hit['lakara'], verb_hit['purusa'], verb_hit['vacana']]
                else:
                    tensor = [cid, POS_VOCAB['verb'], 0, 0, 0, verb_hit['lakara'], verb_hit['purusa'], 1, 0, 0, verb_hit['vacana']]
            
            # Step 0b: Kṛdanta lookup
            if tensor is None:
                krd_hit = self.tinganta_db.lookup_krdanta(word)
                if krd_hit:
                    cid = krd_hit['concept_id']
                    deriv = krd_hit['derivation']
                    pos_val = POS_VOCAB['avyaya'] if deriv in (3, 4) else POS_VOCAB['noun']
                    if self.default_dim == 5:
                        tensor = [cid, pos_val, 0, 0, 0]
                    elif self.default_dim == 7:
                        tensor = [0, cid, deriv, pos_val, 0, 0, 0]
                    else:
                        linga = GENDER_VOCAB['masculine'] if pos_val == POS_VOCAB['noun'] else 0
                        vibhakti = CASE_VOCAB['nominative'] if pos_val == POS_VOCAB['noun'] else 0
                        vacana = NUMBER_VOCAB['singular'] if pos_val == POS_VOCAB['noun'] else 0
                        tensor = [cid, pos_val, 0, deriv, 0, 0, 0, 0, linga, vibhakti, vacana]

            # 1. Try stripping Noun Suffixes
            for suff, (cas, num) in suffix_map_noun.items():
                if word.endswith(suff):
                    stem = word[:-len(suff)]
                    root_id = self.stem_map.get(stem)
                    if not root_id and stem.endswith("k"):
                        # Diminutive pleonastic -ka- stripping (e.g. kuṭumba + ka + am)
                        root_id = self.stem_map.get(stem[:-1])
                    if not root_id:
                        for u in upasargas:
                            if stem.startswith(u):
                                sub = stem[len(u):]
                                root_id = self.stem_map.get(sub)
                                if not root_id and sub.endswith("k"):
                                    root_id = self.stem_map.get(sub[:-1])
                                if root_id:
                                    break
                    if root_id:
                        gender = GENDER_VOCAB["masculine"]
                        derivation_id = 0
                        if word.endswith("ā") or word.endswith("ī") or stem.endswith("ā") or stem.endswith("ī"):
                            gender = GENDER_VOCAB["feminine"]
                        elif word.endswith("m") or word.endswith("ṃ") or stem.endswith("m") or suff in ("am", "āni", "āṇi", "ṃ"):
                            gender = GENDER_VOCAB["neuter"]
                            
                        if self.default_dim == 5:
                            tensor = [root_id, POS_VOCAB["noun"], gender, cas, num]
                        elif self.default_dim == 7:
                            tensor = [0, root_id, 0, POS_VOCAB["noun"], gender, cas, num]
                        else:
                            if root_id == ROOT_VOCAB.get("rāma") or root_id == ROOT_VOCAB.get("ram"):
                                derivation_id = DERIVATION_VOCAB.get("ghañ", 1)
                            tensor = [root_id, POS_VOCAB["noun"], 0, derivation_id, 0, 0, 0, 0, gender, cas, num]
                        break

            # 2. Try stripping Verb Suffixes
            if tensor is None:
                for suff, (pers, num) in suffix_map_verb.items():
                    if word.endswith(suff):
                        stem = word[:-len(suff)]
                        if stem.endswith("a"): stem = stem[:-1]
                        root_id = self.stem_map.get(stem)
                        if not root_id:
                            for u in upasargas:
                                if stem.startswith(u):
                                    sub = stem[len(u):]
                                    root_id = self.stem_map.get(sub)
                                    if root_id: break
                        if root_id:
                            if self.default_dim == 5:
                                tensor = [root_id, POS_VOCAB["verb"], TENSE_VOCAB["present"], pers, num]
                            elif self.default_dim == 7:
                                tensor = [0, root_id, 0, POS_VOCAB["verb"], TENSE_VOCAB["present"], pers, num]
                            else:
                                tensor = [root_id, POS_VOCAB["verb"], 0, 0, 0, TENSE_VOCAB["present"], pers, 1, 0, 0, num]
                            break
            if tensor is None:
                # Direct match with Avyaya precedence
                CLOSED_CLASS_AVYAYAS = {"tu", "ca", "vā", "na", "eva", "api", "iti", "hi", "mā", "saha", "alam", "athavā", "tathā", "yathā", "yadā", "tadā", "kutaḥ", "tatra", "atra", "sarvatra"}
                if word in CLOSED_CLASS_AVYAYAS:
                    try:
                        from sanskrit_engine.pratipadika_db import get_pratipadika
                        prat = get_pratipadika(word)
                        root_id = prat['vector_meta']['concept_id'] if prat else (18511 if word=="tu" else 18451)
                    except Exception:
                        root_id = 18511 if word=="tu" else (18451 if word=="eva" else 18432)
                    pos_id = POS_VOCAB["avyaya"]
                else:
                    root_id = self.stem_map.get(word)
                    if root_id:
                        pos_id = POS_VOCAB["noun"] if (10000 <= root_id <= 89999) else (POS_VOCAB["verb"] if root_id >= 1000000 else POS_VOCAB["avyaya"])
                if root_id:
                    if self.default_dim == 5:
                        tensor = [root_id, pos_id, 0, 0, 0]
                    elif self.default_dim == 7:
                        tensor = [0, root_id, 0, pos_id, 0, 0, 0]
                    else:
                        tensor = [root_id, pos_id, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            
            if tensor is None and allow_oov:
                # Dynamic external / OOV word handling (Non-root words)
                ext_id = 90000 + abs(hash(word)) % 10000
                ROOT_VOCAB[word] = ext_id
                REV_ROOT[ext_id] = word
                self.stem_map[word] = ext_id
                if self.default_dim == 5:
                    tensor = [ext_id, POS_VOCAB["noun"], GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]]
                elif self.default_dim == 7:
                    tensor = [0, ext_id, 0, POS_VOCAB["noun"], GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]]
                else:
                    tensor = [ext_id, POS_VOCAB["noun"], 0, 0, 0, 0, 0, 0, GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]]
                
            if tensor is not None:
                tensors.append(TensorCoordinate(tensor))
                
        return tensors

    def decode(self, coordinates: List[TensorCoordinate]) -> str:
        """
        Decodes a sequence of integer TensorCoordinates back into Sanskrit text natively.
        Supports 5D, 7D, and 11D coordinate tensors.
        """
        words = []
        for coord in coordinates:
            vec = coord.vector
            
            if len(vec) == 5:
                root_id, pos_id, f1, f2, f3 = vec
                upasarga_id, derivation_id = 0, 0
            elif len(vec) == 7:
                upasarga_id, root_id, derivation_id, pos_id, f1, f2, f3 = vec
            elif len(vec) == 11:
                root_id, pos_id, upasarga_id, derivation_id, compound_role, lakara, purusa, pada, linga, vibhakti, vacana = vec
                f1 = lakara if pos_id == POS_VOCAB.get("verb", 2) else linga
                f2 = purusa if pos_id == POS_VOCAB.get("verb", 2) else vibhakti
                f3 = vacana
            else:
                raise ValueError(f"Invalid tensor dimension: {len(vec)}. Must be 5D, 7D, or 11D.")
                
            root_str = REV_ROOT.get(root_id, "unknown")
            pos_str = REV_POS.get(pos_id, "unknown")
            upasarga_str = REV_UPASARGA.get(upasarga_id, "") if upasarga_id != 0 else ""
            derivation_str = REV_DERIVATION.get(derivation_id, "none") if derivation_id != 0 else "none"
            
            if derivation_id != 0:
                surf_krd = self.tinganta_db.lookup_surface_krdanta(root_id, derivation_id)
                derived_stem = surf_krd if surf_krd else self.morphology.derive(root_str, derivation_str)
            else:
                derived_stem = self.morphology.derive(root_str, derivation_str)
            base_string = derived_stem
            
            env = {
                "root": root_str,
                "derived_stem": derived_stem,
                "derivation": derivation_str,
                "pos": pos_str
            }
            
            if 90000 <= root_id <= 99999:
                base_string = derived_stem
            elif pos_str == "noun":
                if f1 == 0 and f2 == 0 and f3 == 0:
                    base_string = derived_stem
                else:
                    env["gender"] = REV_GENDER.get(f1, "masculine")
                    env["case"] = REV_CASE.get(f2, "nominative")
                    env["number"] = REV_NUMBER.get(f3, "singular")
                    
                    entry = NounEntry(derived_stem, env["gender"], "Unknown")
                    base_string = self.morphology.decline(entry, env["case"], env["number"]).text
                
                if upasarga_str:
                    base_string = upasarga_str + base_string
                    
            elif pos_str == "verb":
                env["tense"] = REV_TENSE.get(f1, "present")
                env["person"] = REV_PERSON.get(f2, "third")
                env["number"] = REV_NUMBER.get(f3, "singular")
                
                dhatu_meta = DHATU_META.get(root_str, {"gana": "1", "pada": "P", "settva": "S"})
                env["voice"] = dhatu_meta["pada"]
                env["gana"] = dhatu_meta["gana"]
                env["settva"] = dhatu_meta.get("settva", "S")
                
                # For non-present tenses, look up the pre-compiled surface form
                if env["tense"] != "present":
                    surf_verb = self.tinganta_db.lookup_surface_verb(root_id, f1, f2, f3)
                    base_string = surf_verb if surf_verb else derived_stem
                else:
                    stem_exceptions = {"gam": "gaccha", "paś": "paśya", "sad": "sīda", "sthā": "tiṣṭha", "mnā": "mana", "dā": "dadā", "han": "han"}
                    present_stem = stem_exceptions.get(derived_stem)
                    if not present_stem:
                        if env["gana"] == "1": present_stem = derived_stem + "a"
                        elif env["gana"] == "4": present_stem = derived_stem + "ya"
                        else: present_stem = derived_stem
                        
                    entry = VerbEntry(derived_stem, present_stem, "Unknown")
                    try:
                        base_string = self.morphology.conjugate(entry, env["person"], env["number"], env["tense"], env["voice"], env["settva"]).text
                    except ValueError:
                        base_string = derived_stem
                    
                if upasarga_str:
                    base_string = upasarga_str + base_string
                    
            elif pos_str == "avyaya":
                base_string = derived_stem
                if upasarga_str:
                    base_string = upasarga_str + base_string
            else:
                base_string = "[UNK]"
                
            # Dynamic Matrix Surgery via RuleDB
            if self.rule_db:
                token = {"pos": pos_str, "text": base_string}
                applicable_rules = self.rule_db.get_applicable_rules(token, env)
                for rule in applicable_rules:
                    try:
                        token_new = rule.apply(token, env)
                        if isinstance(token_new, dict):
                            token = token_new
                        elif isinstance(token_new, str):
                            token["text"] = token_new
                    except Exception:
                        pass
                base_string = token["text"]
                
            words.append(base_string)
            
        # External Sandhi
        if self.rule_db and len(words) > 1:
            for i in range(len(words) - 1):
                token = (words[i], words[i+1])
                env = {"pos": "sandhi"}
                applicable_rules = self.rule_db.get_applicable_rules(token, env)
                for rule in applicable_rules:
                    try:
                        token_new = rule.apply(token, env)
                        if isinstance(token_new, tuple) and len(token_new) == 2:
                            token = token_new
                    except Exception:
                        pass
                words[i] = token[0]
                words[i+1] = token[1]
                
        return " ".join(words)
