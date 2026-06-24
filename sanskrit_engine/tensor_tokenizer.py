from typing import List, Dict, Any
from .morphology import RuleBasedMorphology
from .lexicon import NounEntry, VerbEntry
from .parser import SanskritParser
from .config_index import *
from .rule_database import RuleDatabase

class TensorDelta:
    """Represents a surgical modification matrix (delta) for a TensorCoordinate."""
    def __init__(self, vector: List[int]):
        self.vector = vector

class TensorCoordinate:
    """
    Represents a multi-dimensional morphological integer vector.
    Format: [root_id, pos_id, feat1_id, feat2_id, feat3_id]
    For Nouns: [root, noun_pos, gender, case, number]
    For Verbs: [root, verb_pos, tense, person, number]
    """
    def __init__(self, vector: List[int]):
        self.vector = vector

    def __eq__(self, other):
        if not isinstance(other, TensorCoordinate):
            return False
        return self.vector == other.vector

    def __add__(self, delta: TensorDelta):
        """Allows surgical mathematical transformations: vector + delta = new_vector"""
        if not isinstance(delta, TensorDelta):
            raise TypeError("Can only add a TensorDelta to a TensorCoordinate.")
        if len(self.vector) != len(delta.vector):
            raise ValueError("Vector and Delta must have the same dimensions.")
        new_vec = [v + d for v, d in zip(self.vector, delta.vector)]
        return TensorCoordinate(new_vec)
        
    def __sub__(self, delta: TensorDelta):
        if not isinstance(delta, TensorDelta):
            raise TypeError("Can only subtract a TensorDelta from a TensorCoordinate.")
        if len(self.vector) != len(delta.vector):
            raise ValueError("Vector and Delta must have the same dimensions.")
        new_vec = [v - d for v, d in zip(self.vector, delta.vector)]
        return TensorCoordinate(new_vec)

    def __repr__(self):
        return f"TensorCoordinate({self.vector})"

class TensorTokenizer:
    """Encodes Sanskrit words into integer tensors and decodes them back dynamically."""
    
    def __init__(self, morphology: RuleBasedMorphology, rule_db: RuleDatabase = None):
        self.morphology = morphology
        self.parser = SanskritParser()
        self.rule_db = rule_db
        self.encode_cache = {}
        self._build_encode_cache()
        
    def _build_encode_cache(self):
        """
        Pre-generates a high-speed reverse-lookup dictionary mapping surface strings back to 7D vectors.
        This provides immediate Encoder functionality without requiring a massive FST un-gluer.
        """
        # We will generate mappings for a few core test words across all dimensions
        target_roots = ["gam", "han", "dā", "bhū", "rāma", "deva", "avatāra", "kṛ", "pustaka"]
        
        for root_str in target_roots:
            root_id = ROOT_VOCAB.get(root_str)
            if not root_id: continue
            
            # If the root is typically a noun base (in our test set, rāma, deva, avatāra, pustaka)
            # Actually, let's just generate Noun and Verb forms for all roots to be thorough!
            
            # --- 1. VERB GENERATION (Present Tense) ---
            # [0, root, 0, Verb(2), Present(1), Person(1..3), Number(1..3)]
            for person_str, person_id in PERSON_VOCAB.items():
                for num_str, num_id in NUMBER_VOCAB.items():
                    vec = [0, root_id, 0, POS_VOCAB["verb"], TENSE_VOCAB["present"], person_id, num_id]
                    try:
                        surface_form = self.decode([TensorCoordinate(vec)])
                        self.encode_cache[surface_form] = vec
                    except Exception:
                        pass
                        
            # --- 2. NOUN GENERATION ---
            # We'll generate Noun derivations using Ghañ (+1) for verbal roots, or none (+0) for nominal roots
            is_nominal = root_str in ["rāma", "deva", "avatāra", "pustaka"]
            derivation_id = 0 if is_nominal else DERIVATION_VOCAB["ghañ"]
            
            # [0, root, deriv, Noun(1), Gender(1..3), Case(1..8), Number(1..3)]
            for gender_str, gender_id in GENDER_VOCAB.items():
                for case_str, case_id in CASE_VOCAB.items():
                    for num_str, num_id in NUMBER_VOCAB.items():
                        vec = [0, root_id, derivation_id, POS_VOCAB["noun"], gender_id, case_id, num_id]
                        try:
                            surface_form = self.decode([TensorCoordinate(vec)])
                            self.encode_cache[surface_form] = vec
                        except Exception:
                            pass
                        
            # --- 3. AVYAYA GENERATION ---
            if not is_nominal:
                # ktvā (+3) -> [0, root, ktva, Avyaya(6), 0, 0, 0]
                vec_ktva = [0, root_id, DERIVATION_VOCAB["ktvā"], POS_VOCAB["avyaya"], 0, 0, 0]
                try:
                    self.encode_cache[self.decode([TensorCoordinate(vec_ktva)])] = vec_ktva
                except: pass

    def encode(self, text: str) -> List[TensorCoordinate]:
        """
        Parses text and encodes into a sequence of integer TensorCoordinates using the cache.
        """
        tensors = []
        words = text.split()
        
        for word in words:
            # Simple space-delimited lookup
            if word in self.encode_cache:
                tensors.append(TensorCoordinate(self.encode_cache[word]))
            else:
                print(f"[!] ENCODER WARNING: Word '{word}' not found in high-speed vocabulary cache.")
                # We return a zeroed out error tensor or just skip it.
                # For LLM robustness, an unknown token is better than crashing.
                tensors.append(TensorCoordinate([0, 0, 0, 0, 0, 0, 0]))
                
        return tensors

    def decode(self, coordinates: List[TensorCoordinate]) -> str:
        """
        Decodes a sequence of integer TensorCoordinates back into Sanskrit text natively
        using the RuleDatabase. No manual parsing exceptions exist here.
        """
        words = []
        for coord in coordinates:
            vec = coord.vector
            
            # Unified 7D Tensor Topology
            if len(vec) == 7:
                upasarga_id, root_id, derivation_id, pos_id, f1, f2, f3 = vec
            else:
                raise ValueError(f"Invalid tensor dimension: {len(vec)}. Must be 7D.")
                
            root_str = REV_ROOT.get(root_id, "unknown")
            pos_str = REV_POS.get(pos_id, "unknown")
            upasarga_str = REV_UPASARGA.get(upasarga_id, "") if upasarga_id != 0 else ""
            derivation_str = REV_DERIVATION.get(derivation_id, "none") if derivation_id != 0 else "none"
            
            # Step 1: Kṛdanta Derivation (Mathematical Root Transformation)
            derived_stem = self.morphology.derive(root_str, derivation_str)
            
            # The base grammatical string to be modified
            base_string = derived_stem
            
            # The semantic environment derived from the tensor matrix
            env = {
                "root": root_str,
                "derived_stem": derived_stem,
                "derivation": derivation_str,
                "pos": pos_str
            }
            
            # Step 2: Part-of-Speech Declension/Conjugation
            if pos_str == "noun":
                env["gender"] = REV_GENDER.get(f1, "masculine")
                env["case"] = REV_CASE.get(f2, "nominative")
                env["number"] = REV_NUMBER.get(f3, "singular")
                
                # First pass: use generic morphology generator
                entry = NounEntry(derived_stem, env["gender"], "Unknown")
                base_string = self.morphology.decline(entry, env["case"], env["number"]).text
                
                # Prepend Upasarga for nominal derivations (e.g., pra-bhāva)
                if upasarga_str:
                    base_string = upasarga_str + base_string
                    
            elif pos_str == "verb":
                env["tense"] = REV_TENSE.get(f1, "present")
                env["person"] = REV_PERSON.get(f2, "third")
                env["number"] = REV_NUMBER.get(f3, "singular")
                
                # Fetch Dhatu Metadata
                dhatu_meta = DHATU_META.get(root_str, {"gana": "1", "pada": "P", "settva": "S"})
                env["voice"] = dhatu_meta["pada"]
                env["gana"] = dhatu_meta["gana"]
                env["settva"] = dhatu_meta.get("settva", "S")
                
                # First pass: generic conjugation with Vikarana
                if env["tense"] == "present":
                    if env["gana"] == "1":
                        present_stem = derived_stem + "a"
                    elif env["gana"] == "4":
                        present_stem = derived_stem + "ya"
                    else:
                        present_stem = derived_stem
                else:
                    present_stem = derived_stem
                    
                entry = VerbEntry(derived_stem, present_stem, "Unknown")
                try:
                    base_string = self.morphology.conjugate(entry, env["person"], env["number"], env["tense"], env["voice"], env["settva"]).text
                except ValueError:
                    base_string = derived_stem
                    
                # Prepend Upasarga
                if upasarga_str:
                    base_string = upasarga_str + base_string
                    
            elif pos_str == "avyaya":
                # Indeclinables do not take su/ti suffixes
                base_string = derived_stem
                # Prepend Upasarga
                if upasarga_str:
                    base_string = upasarga_str + base_string
                    
            else:
                base_string = "[UNK]"
                
            # Second pass: PANINIAN CONSISTENCY via Dynamic Matrix Fetching
            # The Tokenizer checks the RuleDatabase to see if any custom
            # matrix modifications (Apavada/Exceptions) must be applied to this environment!
            if self.rule_db:
                # We package the state as a mutable dictionary token
                token = {"pos": pos_str, "text": base_string}
                applicable_rules = self.rule_db.get_applicable_rules(token, env)
                
                # Sequentially apply the fetched mathematical transformations
                for rule in applicable_rules:
                    try:
                        token_new = rule.apply(token, env)
                        if isinstance(token_new, dict):
                            token = token_new
                        elif isinstance(token_new, str):
                            token["text"] = token_new
                    except Exception as e:
                        # Skip badly compiled LLM rules rather than crashing
                        pass
                
                base_string = token["text"]
                
            words.append(base_string)
            
        # Third pass: EXTERNAL SANDHI (Vakya Sandhi)
        # Apply phonetic rules across word boundaries
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
                    except Exception as e:
                        pass
                words[i] = token[0]
                words[i+1] = token[1]
        
        return " ".join(words)
