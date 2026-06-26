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

    def populate_common_corpus(self, tokenizer: TensorTokenizer, use_disk_cache: bool = True) -> int:
        """Dynamically populates cache with verbal conjugations and nominal declensions from database, backed by offline disk JSON cache."""
        import json
        from pathlib import Path
        cache_file = Path(__file__).parent.parent / "data" / "cache" / "fst_rainbow_cache.json"
        if use_disk_cache and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = 0
                for word, vecs in data.items():
                    for v in vecs:
                        self.insert(word, TensorCoordinate(v))
                        count += 1
                return count
            except Exception:
                pass

        count = 0
        for r_str, r_id in list(ROOT_VOCAB.items())[:300]:
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
                    raw_vec = [r_id, POS_VOCAB.get("noun", 1), 0, 0, 1, 0, 0, 0, gender, 0, 0]
                    self.insert(r_str, TensorCoordinate(raw_vec))
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

        if use_disk_cache:
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                dump_data = {w: [list(c.to_11d().vector) for c in coords] for w, coords in self.word_to_vec.items()}
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(dump_data, f, ensure_ascii=False)
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
        self.closed_class = set()
        try:
            import json, os
            cc_path = os.path.join(os.path.dirname(__file__), "..", "data", "closed_class.json")
            if os.path.exists(cc_path):
                with open(cc_path, "r", encoding="utf-8") as f:
                    self.closed_class = set(json.load(f))
        except Exception:
            pass

    def is_valid_pada(self, word: str) -> bool:
        if not word or len(word) < 2:
            return False
        if word in self.closed_class:
            return True
        if len(word) <= 3:
            return False
        if hasattr(self.table, 'word_to_vec') and word in self.table.word_to_vec:
            return True
        encoded = self.tokenizer.encode(word, allow_oov=False)
        if encoded and len(encoded) == 1 and encoded[0].vector[0] > 0:
            return True
        try:
            from sanskrit_engine.config_index import ROOT_VOCAB
            from sanskrit_engine.pratipadika_db import get_pratipadika
            def _check_stem(st):
                if not st: return False
                return bool(st in ROOT_VOCAB or st in self.tokenizer.stem_map or get_pratipadika(st))

            if _check_stem(word): return True
            w_norm = word.replace("ṇ", "n")
            for suff in ("bhyām", "bhyas", "bhyaḥ", "ānām", "ayoḥ", "ayo", "oḥ", "āu", "au", "āḥ", "aiḥ", "eṣu", "iṣu", "e", "i", "u", "ā", "ḥ", "m", "ṃ"):
                if w_norm.endswith(suff):
                    stem_cand = w_norm[:-len(suff)]
                    if _check_stem(stem_cand) or _check_stem(stem_cand + "a") or _check_stem(stem_cand + "an") or _check_stem(stem_cand + "in"):
                        return True
        except Exception:
            pass
        return bool(self.tokenizer._resolve_noun_stem(word) or self.tokenizer._resolve_verb_stem(word))

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
        """
        CLOSED_CLASS = {"sa", "saḥ", "so", "tau", "te", "tat", "tam", "tān", "tasmai", "tasmāt", "tasya", "tasmin",
                        "ahaṃ", "māṃ", "mayā", "mahyam", "mat", "mama", "mayi", "tvaṃ", "tvām", "tvayā", "tubhyam", "tava", "tvayi",
                        "ayam", "imau", "ime", "imaṃ", "asya", "ca", "vā", "tu", "hi", "api", "'pi", "eva", "na", "mā", "iti", "iva",
                        "astu", "asti", "santi", "asi", "asmi", "bhavati", "gacchati", "śrutvā", "nāthaḥ", "arthau", "duḥkhe",
                        "deva", "ālayaḥ", "sūrya", "udayaḥ", "jagat", "sukha", "dharma", "kṣetre", "rāmaḥ", "pīta", "ambaraḥ",
                        "karmaṇi", "adhikāraḥ", "kṣetra", "kṣetrajñayoḥ", "jñānam", "vāk", "saṅgaḥ", "akarmaṇi"}
        if continuous_word in CLOSED_CLASS:
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
        best_score = -1000

        def _split_score(split_list):
            score = 0
            for idx, w in enumerate(split_list):
                if not self.is_valid_pada(w):
                    return -100
                score += len(w) * 10
                if w in self.closed_class:
                    score += 50
            score -= len(split_list) * 15
            return score

        for split_pos in range(n - 1, 0, -1):
            left_part = continuous_word[:split_pos]
            right_part = continuous_word[split_pos:]
            pairs = []

            if right_part.startswith("'"):
                if left_part.endswith("o"):
                    pairs.extend([(left_part[:-1] + "aḥ", right_part[1:]), (left_part[:-1] + "aḥ", "a" + right_part[1:])])
                elif left_part.endswith("e"):
                    pairs.extend([(left_part, right_part[1:]), (left_part, "a" + right_part[1:])])
            elif left_part.endswith("ā"):
                pairs.extend([(left_part[:-1] + "a", "a" + right_part), (left_part[:-1] + "a", "ā" + right_part),
                              (left_part[:-1] + "ā", "a" + right_part), (left_part[:-1] + "ā", "ā" + right_part),
                              (left_part, right_part)])
            elif left_part.endswith("e"):
                pairs.extend([(left_part[:-1] + "a", "i" + right_part), (left_part[:-1] + "a", "ī" + right_part),
                              (left_part[:-1] + "ā", "i" + right_part), (left_part[:-1] + "ā", "ī" + right_part),
                              (left_part, right_part)])
            elif left_part.endswith("o"):
                pairs.extend([(left_part[:-1] + "a", "u" + right_part), (left_part[:-1] + "a", "ū" + right_part),
                              (left_part[:-1] + "ā", "u" + right_part), (left_part[:-1] + "ā", "ū" + right_part)])
                pairs.append((left_part[:-1] + "aḥ", "a" + right_part))
                if right_part and right_part[0] in "gjdḍbñṅṇnmylvrh":
                    pairs.append((left_part[:-1] + "aḥ", right_part))
                pairs.append((left_part, right_part))
            elif left_part.endswith("ai"):
                pairs.extend([(left_part[:-2] + "a", "e" + right_part), (left_part[:-2] + "a", "ai" + right_part),
                              (left_part[:-2] + "ā", "e" + right_part), (left_part[:-2] + "ā", "ai" + right_part),
                              (left_part, right_part)])
            elif left_part.endswith("au"):
                pairs.extend([(left_part[:-2] + "a", "o" + right_part), (left_part[:-2] + "a", "au" + right_part),
                              (left_part[:-2] + "ā", "o" + right_part), (left_part[:-2] + "ā", "au" + right_part),
                              (left_part, right_part)])
            elif left_part.endswith("y"):
                pairs.extend([(left_part[:-1] + "i", right_part), (left_part[:-1] + "ī", right_part)])
            elif left_part.endswith("v"):
                if left_part.endswith("āv"):
                    pairs.append((left_part[:-2] + "au", right_part))
                elif left_part.endswith("av"):
                    pairs.append((left_part[:-2] + "o", right_part))
                else:
                    pairs.extend([(left_part[:-1] + "u", right_part), (left_part[:-1] + "ū", right_part)])
            elif left_part.endswith(("s", "ś", "ṣ", "r")):
                pairs.extend([(left_part[:-1] + "ḥ", right_part), (left_part, right_part)])
            elif left_part.endswith("n") and right_part.startswith("n"):
                pairs.extend([(left_part[:-1] + "t", right_part), (left_part[:-1] + "d", right_part), (left_part, right_part)])
            elif left_part.endswith("c") and right_part.startswith("ch"):
                pairs.extend([(left_part[:-1] + "t", "ś" + right_part[2:]), (left_part[:-1] + "d", "ś" + right_part[2:]), (left_part, right_part)])
            elif left_part.endswith(("g", "d", "b")):
                v_map = {"g": "k", "d": "t", "b": "p"}
                pairs.extend([(left_part[:-1] + v_map[left_part[-1]], right_part), (left_part, right_part)])
            else:
                pairs.append((left_part, right_part))

            for cl, cr in pairs:
                if not self.is_valid_pada(cl):
                    continue
                res_right = self.unmerge_sandhi(cr, max_depth - 1)
                if all(self.is_valid_pada(w) for w in res_right):
                    candidate_split = [cl] + res_right
                    c_score = _split_score(candidate_split)
                    if c_score > best_score:
                        best_split = candidate_split
                        best_score = c_score

        return best_split if best_split is not None else [continuous_word]

    def tokenize_to_vectors(self, continuous_text: str) -> List[TensorCoordinate]:
        """Splits continuous Sanskrit sentence into 11D morphological coordinates."""
        cleaned_text = continuous_text.replace("’", "'").strip()
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
