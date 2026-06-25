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
                for c_name, c_id in list(CASE_VOCAB.items())[:8]:
                    for n_name, n_id in list(NUMBER_VOCAB.items())[:3]:
                        vec = [r_id, POS_VOCAB.get("noun", 1), 0, 0, 0, 0, 0, 0, GENDER_VOCAB.get("masculine", 1), c_id, n_id]
                        coord = TensorCoordinate(vec)
                        try:
                            surf = tokenizer.decode([coord])
                            self.insert(surf, coord)
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
        if word in self.table.word_to_vec:
            return True
        # Check if it has a valid suffix using tokenizer
        encoded = self.tokenizer.encode(word, allow_oov=False)
        if encoded and len(encoded) == 1:
            cid = encoded[0].vector[0]
            if cid > 0 and not (90000 <= cid <= 99999):
                pos = encoded[0].vector[1] if len(encoded[0].vector) > 1 else 0
                vibhakti = encoded[0].vector[9] if len(encoded[0].vector) > 9 else 0
                if pos == 6 or vibhakti > 0 or (word in self.tokenizer.stem_map and len(word) >= 3):
                    return True
        return False

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
            
        intercepted = self.intercept_nominal_prefixes(continuous_word)
        if intercepted:
            return intercepted
            
        if max_depth <= 0 or len(continuous_word) <= 2:
            return [continuous_word]

        n = len(continuous_word)
        best_split = None
        AVYAYAS = {"a", "sa", "ca", "tu", "hi", "mā", "vā", "api", "iti", "na", "eva"}

        for split_pos in range(1, n):
            left_part = continuous_word[:split_pos]
            right_part = continuous_word[split_pos:]

            # Heuristic Sandhi boundary unmerging
            candidates_left = [left_part]
            candidates_right = [right_part]
            if left_part.endswith("ā"):
                candidates_left.append(left_part[:-1] + "a")
                candidates_right.append("a" + right_part)
                candidates_right.append("ā" + right_part)
            elif left_part.endswith("e"):
                candidates_left.append(left_part[:-1] + "a")
                candidates_right.append("i" + right_part)
                candidates_right.append("ī" + right_part)
            elif left_part.endswith("o"):
                candidates_left.append(left_part[:-1] + "a")
                candidates_right.append("u" + right_part)
                candidates_right.append("ū" + right_part)
            elif left_part.endswith("ai"):
                candidates_left.append(left_part[:-2] + "a")
                candidates_left.append(left_part[:-2] + "ā")
                candidates_right.append("e" + right_part)
                candidates_right.append("ai" + right_part)
            elif left_part.endswith("y"):
                candidates_left.append(left_part[:-1] + "i")
                candidates_right.append(right_part)
            elif left_part.endswith("s") or left_part.endswith("ś") or left_part.endswith("ṣ"):
                candidates_left.append(left_part[:-1] + "ḥ")
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
        raw_words = continuous_text.split()
        split_words: List[str] = []
        for rw in raw_words:
            split_words.extend(self.unmerge_sandhi(rw))

        vectors: List[TensorCoordinate] = []
        for sw in split_words:
            cached = self.table.lookup_word(sw)
            if cached:
                vectors.append(cached[0].to_11d())
            else:
                encoded = self.tokenizer.encode(sw)
                if encoded:
                    vectors.append(encoded[0].to_11d())
        return vectors
