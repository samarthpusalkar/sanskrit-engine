"""
Bidirectional Word2Vec and Vec2Word Engine with FST/Trie Cache.
Provides O(1) vectorized morphological lookups and Sandhi splitting.
Consistent with 11D Tensor Coordinate Contract [V0..V10].
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from .config_index import *
from .tensor_tokenizer import TensorCoordinate, TensorTokenizer


class TrieNode:
    """Node in Fast String Trie (FST) for prefix matching and O(1) lookups."""
    def __init__(self) -> None:
        self.children: Dict[str, TrieNode] = {}
        self.is_end_of_word: bool = False
        self.coordinates: List[TensorCoordinate] = []


class RainbowTableGenerator:
    """
    Generates and indexes exhaustive surface form <-> 11D Tensor mappings.
    Acts as a precompiled FST lookup table avoiding runtime derivation overhead.
    """
    def __init__(self) -> None:
        self.root = TrieNode()
        self.vec_to_word: Dict[Tuple[int, ...], str] = {}
        self.word_to_vec: Dict[str, List[TensorCoordinate]] = {}

    def insert(self, word: str, coord: TensorCoordinate) -> None:
        """Inserts a word and its vector coordinate into the Trie and reverse index."""
        norm_vec = tuple(coord.to_11d().vector)
        self.vec_to_word[norm_vec] = word
        if word not in self.word_to_vec:
            self.word_to_vec[word] = []
        self.word_to_vec[word].append(coord)

        # Trie Insertion
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.coordinates.append(coord)

    def lookup_word(self, word: str) -> List[TensorCoordinate]:
        """O(1) dictionary lookup of all morphological vectors for a surface word."""
        return self.word_to_vec.get(word, [])

    def lookup_vector(self, coord: TensorCoordinate) -> Optional[str]:
        """O(1) reverse lookup of surface form given an 11D vector coordinate."""
        norm_vec = tuple(coord.to_11d().vector)
        return self.vec_to_word.get(norm_vec)

    def populate_common_corpus(self, tokenizer: TensorTokenizer) -> int:
        """Dynamically populates cache with verbal conjugations and nominal declensions from database."""
        count = 0
        for r_str, r_id in list(ROOT_VOCAB.items())[:200]:
            if r_str in DHATU_META:
                for p_name, p_id in list(PERSON_VOCAB.items())[:3]:
                    for n_name, n_id in list(NUMBER_VOCAB.items())[:3]:
                        vec = [r_id, POS_VOCAB.get("verb", 2), 0, 0, 0, TENSE_VOCAB.get("present", 1), p_id, 1, 0, 0, n_id]
                        coord = TensorCoordinate(vec)
                        try:
                            surf = tokenizer.decode([coord])
                            self.insert(surf, coord)
                            count += 1
                        except Exception:
                            pass
            else:
                is_avyaya = r_str in ("tu", "ca", "vā", "na", "eva", "api", "iti", "hi", "mā", "saha", "alam")
                gender = GENDER_VOCAB.get("masculine", 1)
                try:
                    from sanskrit_engine.pratipadika_db import get_pratipadika
                    pr = get_pratipadika(r_str)
                    if pr:
                        if pr.get('paninian_meta', {}).get('is_avyaya'): is_avyaya = True
                        gl = pr.get('pos_flags', {}).get('allowed_genders', [])
                        if 'N' in gl: gender = GENDER_VOCAB.get("neuter", 3)
                        elif 'F' in gl: gender = GENDER_VOCAB.get("feminine", 2)
                except Exception:
                    pass
                if is_avyaya:
                    vec = [r_id, POS_VOCAB.get("avyaya", 6), 0, 0, 0, 0, 0, 0, 0, 0, 0]
                    self.insert(r_str, TensorCoordinate(vec))
                    count += 1
                else:
                    for c_name, c_id in list(CASE_VOCAB.items())[:8]:
                        for n_name, n_id in list(NUMBER_VOCAB.items())[:3]:
                            vec = [r_id, POS_VOCAB.get("noun", 1), 0, 0, 0, 0, 0, 0, gender, c_id, n_id]
                            coord = TensorCoordinate(vec)
                            try:
                                surf = tokenizer.decode([coord])
                                self.insert(surf, coord)
                                if r_str.endswith("u") and c_id in (5, 6) and n_id == 1:
                                    self.insert(r_str[:-1] + "oḥ", coord)
                                count += 1
                            except Exception:
                                pass
        return count


class SandhiSplitterTokenizer:
    """
    Splits continuous Sandhi text into constituent words using FST Trie prefix match
    and reverse Sandhi boundary rules.
    """
    def __init__(self, rainbow_table: RainbowTableGenerator, tokenizer: TensorTokenizer) -> None:
        self.table = rainbow_table
        self.tokenizer = tokenizer

    def is_valid_pada(self, word: str) -> bool:
        if hasattr(self.table, 'word_to_vec') and word in self.table.word_to_vec:
            return True
        encoded = self.tokenizer.encode(word, allow_oov=False)
        return bool(encoded and len(encoded) == 1 and encoded[0].vector[0] > 0)

    def intercept_nominal_prefixes(self, word: str) -> Optional[List[str]]:
        NOMINAL_PREFIXES = {
            "a": "nan_negative",
            "an": "nan_negative",
            "su": "pradi_good",
            "ku": "pradi_bad",
            "sa": "saha_inclusive",
            "prati": "avyaya_every",
            "yathā": "avyaya_according",
            "dur": "pradi_difficult", 
            "dus": "pradi_difficult",
            "duṣ": "pradi_difficult"
        }
        sorted_prefixes = sorted(NOMINAL_PREFIXES.keys(), key=len, reverse=True)
        for prefix in sorted_prefixes:
            if word.startswith(prefix):
                base_candidate = word[len(prefix):]
                if self.is_valid_pada(base_candidate):
                    if prefix == "an" and (not base_candidate or base_candidate[0] not in "aāiīuūṛṝeoaiou"):
                        continue
                    if prefix == "a" and (not base_candidate or base_candidate[0] in "aāiīuūṛṝeoaiou"):
                        continue
                    return [prefix, base_candidate]
        return None

    def unmerge_sandhi(self, continuous_word: str, max_depth: int = 4) -> List[str]:
        """
        Greedily attempts to split a compound/sandhi word into valid cached padas.
        E.g., 'devāvatāraḥ' -> ['deva', 'avatāraḥ']
        """
        if self.is_valid_pada(continuous_word):
            return [continuous_word]
            
        # Isolated word-final external Sandhi normalization (e.g., asato -> asataḥ, sad -> sat)
        norm_candidates = []
        if continuous_word.endswith("o"):
            norm_candidates.append(continuous_word[:-1] + "aḥ")
        elif continuous_word.endswith(("r", "s", "ś", "ṣ")):
            norm_candidates.append(continuous_word[:-1] + "ḥ")
        elif continuous_word.endswith("d"):
            norm_candidates.append(continuous_word[:-1] + "t")
        elif continuous_word.endswith("g"):
            norm_candidates.append(continuous_word[:-1] + "k")
        elif continuous_word.endswith("b"):
            norm_candidates.append(continuous_word[:-1] + "p")
            
        for nc in norm_candidates:
            if self.is_valid_pada(nc):
                return [nc]
            
        intercepted = self.intercept_nominal_prefixes(continuous_word)
        if intercepted:
            return intercepted
            
        if max_depth <= 0 or len(continuous_word) <= 2:
            return [continuous_word]

        n = len(continuous_word)
        best_split = None
        AVYAYAS = {"a", "sa", "ca", "tu", "hi", "mā", "vā", "api", "iti", "na", "eva"}

        for split_pos in range(n - 1, 0, -1):
            left_part = continuous_word[:split_pos]
            right_part = continuous_word[split_pos:]

            # Heuristic Sandhi boundary unmerging
            candidates_left = []
            candidates_right = []
            if left_part.endswith("ā"):
                candidates_left.extend((left_part[:-1] + "a", left_part))
                candidates_right.extend(("a" + right_part, "ā" + right_part, right_part))
            elif left_part.endswith("e"):
                candidates_left.extend((left_part[:-1] + "a", left_part))
                candidates_right.extend(("i" + right_part, "ī" + right_part, right_part))
            elif left_part.endswith("o"):
                candidates_left.extend((left_part[:-1] + "aḥ", left_part[:-1] + "a", left_part))
                candidates_right.extend(("a" + right_part, "u" + right_part, "ū" + right_part, right_part))
            elif left_part.endswith("ai"):
                candidates_left.extend((left_part[:-2] + "a", left_part[:-2] + "ā", left_part))
                candidates_right.extend(("e" + right_part, "ai" + right_part))
            elif left_part.endswith("y"):
                candidates_left.extend((left_part[:-1] + "i", left_part))
                candidates_right.append(right_part)
            elif left_part.endswith("v"):
                candidates_left.extend((left_part[:-1] + "u", left_part))
                candidates_right.append(right_part)
            elif left_part.endswith(("s", "ś", "ṣ", "r")):
                candidates_left.extend((left_part[:-1] + "ḥ", left_part))
                candidates_right.append(right_part)
            else:
                candidates_left.append(left_part)
                candidates_right.append(right_part)

            for cl in candidates_left:
                if len(cl) < 2 and cl not in AVYAYAS:
                    continue
                if self.is_valid_pada(cl):
                    for cr in candidates_right:
                        res_right = self.unmerge_sandhi(cr, max_depth - 1)
                        if all((len(w) > 1 or w in AVYAYAS) and self.is_valid_pada(w) for w in res_right):
                            candidate_split = [cl] + res_right
                            if best_split is None or len(candidate_split) < len(best_split):
                                best_split = candidate_split

        return best_split if best_split is not None else [continuous_word]

    def tokenize_to_vectors(self, continuous_text: str) -> List[TensorCoordinate]:
        """Splits continuous Sanskrit sentence into 11D morphological coordinates."""
        cleaned_text = continuous_text.replace("’", "a").replace("'", "a").replace("'", "a").strip()
        raw_words = cleaned_text.split()
        split_words: List[str] = []
        for rw in raw_words:
            split_words.extend(self.unmerge_sandhi(rw))

        vectors: List[TensorCoordinate] = []
        for sw in split_words:
            cached = self.table.lookup_word(sw) if hasattr(self.table, 'lookup_word') else None
            if cached:
                vectors.append(cached[0].to_11d())
            else:
                encoded = self.tokenizer.encode(sw)
                if encoded:
                    vectors.append(encoded[0].to_11d())
        return vectors
