import json
import os

# Base Vocabulary (Dynamic)
ROOT_VOCAB = {}
REV_ROOT = {}
DHATU_META = {}

POS_VOCAB = {
    "noun": 1,
    "verb": 2,
    "prefix": 3,
    "sandhi_modifier": 4,
    "samasa_component": 5,
    "avyaya": 6
}

DERIVATION_VOCAB = {
    "none": 0,
    "ghañ": 1,   # Verb -> Noun (Action/Abstract)
    "lyuṭ": 2,   # Verb -> Noun (Instrument/Action)
    "ktvā": 3,   # Verb -> Avyaya (Gerund, having done)
    "tumun": 4   # Verb -> Avyaya (Infinitive, to do)
}

# --- Verbal Transformations ---
TENSE_VOCAB = {
    "present": 1,   # laṭ
    "perfect": 2,   # liṭ
    "future": 3,    # lṛṭ
    "imperative": 4 # loṭ
}

PERSON_VOCAB = {
    "third": 1,  # prathama
    "second": 2, # madhyama
    "first": 3   # uttama
}

NUMBER_VOCAB = {
    "singular": 1,
    "dual": 2,
    "plural": 3
}

# --- Nominal Transformations ---
CASE_VOCAB = {
    "nominative": 1,
    "accusative": 2,
    "instrumental": 3,
    "dative": 4,
    "ablative": 5,
    "genitive": 6,
    "locative": 7,
    "vocative": 8
}

GENDER_VOCAB = {
    "masculine": 1,
    "feminine": 2,
    "neuter": 3
}

# --- Upasargas (Prefixes) ---
UPASARGA_VOCAB = {
    "none": 0, "pra": 1, "parā": 2, "apa": 3, "sam": 4, 
    "anu": 5, "ava": 6, "nis": 7, "nir": 8, "dus": 9, 
    "dur": 10, "vi": 11, "ā": 12, "ni": 13, "adhi": 14, 
    "api": 15, "ati": 16, "su": 17, "ud": 18, "abhi": 19, 
    "prati": 20, "pari": 21, "upa": 22
}

def populate_vocabularies(dhatu_filepath: str = None):
    """
    Dynamically loads the massive Dhatupatha (and opaque nouns) into the ROOT_VOCAB.
    """
    global ROOT_VOCAB, REV_ROOT, DHATU_META
    ROOT_VOCAB.clear()
    REV_ROOT.clear()
    DHATU_META.clear()

    # 1. Load Prātipadikas from indexed SQLite database / fallback JSON
    try:
        from sanskrit_engine.pratipadika_db import _DEFAULT_DB
        _DEFAULT_DB.load_into_vocab(ROOT_VOCAB, REV_ROOT)
    except Exception as e:
        pass

    # 2. Load Dhātus from JSON Dhātupāṭha database
    base_data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    opt_dhatu = dhatu_filepath or os.path.join(base_data_dir, "optimized_dhatu.json")
    if not os.path.exists(opt_dhatu):
        opt_dhatu = os.path.join(base_data_dir, "dhatu_data.json")

    if os.path.exists(opt_dhatu):
        try:
            with open(opt_dhatu, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                dhatu_list = raw_data if isinstance(raw_data, list) else raw_data.get("data", [])
                
                try:
                    from indic_transliteration import sanscript
                except ImportError:
                    sanscript = None

                max_id = max(ROOT_VOCAB.values()) if ROOT_VOCAB else 10000

                for item in dhatu_list:
                    if "morphology" in item:
                        cid = item.get("vector_meta", {}).get("concept_id")
                        morph = item.get("morphology", {})
                        iast = morph.get("dhatu_iast")
                        dev = morph.get("dhatu_dev")
                        slp1 = morph.get("dhatu_slp1")
                        if cid and iast:
                            ROOT_VOCAB[iast] = cid
                            if dev: ROOT_VOCAB[dev] = cid
                            if slp1: ROOT_VOCAB[slp1] = cid
                            REV_ROOT[cid] = iast
                            flags = item.get("compiler_flags", {})
                            DHATU_META[iast] = {
                                "gana": str(flags.get("gana", 1)),
                                "pada": flags.get("pada", "P"),
                                "settva": flags.get("settva", "S")
                            }
                            if dev: DHATU_META[dev] = DHATU_META[iast]
                    else:
                        d_name_dev = item.get("dhatu")
                        aup_dev = item.get("aupadeshik", "")
                        if d_name_dev:
                            if sanscript:
                                d_iast = sanscript.transliterate(d_name_dev, sanscript.DEVANAGARI, sanscript.IAST)
                                aup_iast = sanscript.transliterate(aup_dev, sanscript.DEVANAGARI, sanscript.IAST) if aup_dev else d_iast
                            else:
                                d_iast = d_name_dev
                                aup_iast = aup_dev
                                
                            if d_iast not in ROOT_VOCAB:
                                max_id += 1
                                ROOT_VOCAB[d_iast] = max_id
                            ROOT_VOCAB[d_name_dev] = ROOT_VOCAB[d_iast]
                            REV_ROOT[ROOT_VOCAB[d_iast]] = d_iast
                            
                            pada = "U" if aup_iast.endswith("ñ") else ("A" if aup_iast.endswith("ṅ") else item.get("pada", "P"))
                            DHATU_META[d_iast] = {
                                "gana": str(item.get("gana", "1")),
                                "pada": pada,
                                "settva": item.get("settva", "S")
                            }
                            DHATU_META[d_name_dev] = DHATU_META[d_iast]
        except Exception as e:
            pass

    # Ensure REV_ROOT mapping exists for every loaded vocabulary token
    for k, v in ROOT_VOCAB.items():
        if v not in REV_ROOT:
            REV_ROOT[v] = k

# Initial population using static defaults
populate_vocabularies()

# Reverse Vocabularies for Decoding
REV_POS = {v: k for k, v in POS_VOCAB.items()}
REV_TENSE = {v: k for k, v in TENSE_VOCAB.items()}
REV_PERSON = {v: k for k, v in PERSON_VOCAB.items()}
REV_NUMBER = {v: k for k, v in NUMBER_VOCAB.items()}
REV_CASE = {v: k for k, v in CASE_VOCAB.items()}
REV_GENDER = {v: k for k, v in GENDER_VOCAB.items()}
REV_UPASARGA = {v: k for k, v in UPASARGA_VOCAB.items()}
REV_DERIVATION = {v: k for k, v in DERIVATION_VOCAB.items()}
