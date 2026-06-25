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
        self.stem_map = {}
        self._build_stem_map()
        
    def _build_stem_map(self):
        """
        Builds a fast reverse Stem Map (O(N) initialization) mapping mathematically derived base stems
        (e.g., 'gacch', 'rama') back to their pure Root IDs, evaluating only 2 states per root.
        """
        self.stem_map = {}
        for root_str, root_id in ROOT_VOCAB.items():
            self.stem_map[root_str] = root_id
            
            # Find Present Tense Stem
            vec = [0, root_id, 0, POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]]
            try:
                surface = self.decode([TensorCoordinate(vec)]) 
                stem = surface
                if surface.endswith("anti"): stem = surface[:-4]
                elif surface.endswith("ante"): stem = surface[:-4]
                elif surface.endswith("ti"): stem = surface[:-2]
                elif surface.endswith("te"): stem = surface[:-2]
                
                # Cache both with and without vikarana 'a'
                if stem.endswith("a"):
                    self.stem_map[stem[:-1]] = root_id
                self.stem_map[stem] = root_id
            except: pass
            
            # Find Nominal Stem
            is_nominal = root_str in ["rāma", "deva", "avatāra", "pustaka"]
            derivation_id = 0 if is_nominal else DERIVATION_VOCAB["ghañ"]
            vec_noun = [0, root_id, derivation_id, POS_VOCAB["noun"], GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]]
            try:
                surface = self.decode([TensorCoordinate(vec_noun)])
                if surface.endswith("ḥ"):
                    self.stem_map[surface[:-1]] = root_id
            except: pass

    def encode(self, text: str) -> List[TensorCoordinate]:
        """
        Parses text and encodes into integer TensorCoordinates using an Inverse Suffix Parser.
        """
        tensors = []
        words = text.split()
        
        # Mapping common suffixes for inverse parsing (Prototype)
        suffix_map_verb = {
            "anti": (PERSON_VOCAB["third"], NUMBER_VOCAB["plural"]),
            "ante": (PERSON_VOCAB["third"], NUMBER_VOCAB["plural"]),
            "ti": (PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]),
            "te": (PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]),
        }
        suffix_map_noun = {
            "sya": (CASE_VOCAB["genitive"], NUMBER_VOCAB["singular"]),
            "am": (CASE_VOCAB["accusative"], NUMBER_VOCAB["singular"]),
            "ḥ": (CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]),
        }
        
        for word in words:
            tensor = None
            
            # 1. Try stripping Verb Suffixes
            for suff, (pers, num) in suffix_map_verb.items():
                if word.endswith(suff):
                    stem = word[:-len(suff)]
                    if stem.endswith("a"): stem = stem[:-1] # strip class vikarana
                    root_id = self.stem_map.get(stem)
                    if root_id:
                        tensor = [0, root_id, 0, POS_VOCAB["verb"], TENSE_VOCAB["present"], pers, num]
                        break
            
            # 2. Try stripping Noun Suffixes
            if tensor is None:
                for suff, (cas, num) in suffix_map_noun.items():
                    if word.endswith(suff):
                        stem = word[:-len(suff)]
                        root_id = self.stem_map.get(stem)
                        if root_id:
                            is_nominal = root_id in [5, 6, 7, 9] # Static nouns
                            derivation_id = 0 if is_nominal else DERIVATION_VOCAB["ghañ"]
                            gender = GENDER_VOCAB["neuter"] if suff == "am" and is_nominal else GENDER_VOCAB["masculine"]
                            tensor = [0, root_id, derivation_id, POS_VOCAB["noun"], gender, cas, num]
                            break
            if tensor is None:
                # Direct match
                root_id = self.stem_map.get(word)
                if root_id:
                    tensor = [0, root_id, 0, POS_VOCAB["avyaya"], 0, 0, 0]
            
            if tensor is None:
                print(f"[!] ENCODER WARNING: Inverse Parser failed to strip suffix for '{word}'.")
                tensor = [0, 0, 0, 0, 0, 0, 0]
                
            tensors.append(TensorCoordinate(tensor))
                
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
