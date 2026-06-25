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
    
    # Initialize with core test words
    ROOT_VOCAB.update({
        "gam": 1, "han": 2, "dā": 3, "bhū": 4, 
        "rāma": 5, "deva": 6, "avatāra": 7, "kṛ": 8, "pustaka": 9
    })
    
    # Defaults for core test words
    DHATU_META.update({
        "gam": {"gana": "1", "pada": "P", "settva": "S"},
        "han": {"gana": "2", "pada": "P", "settva": "A"},
        "dā": {"gana": "3", "pada": "U", "settva": "A"},
        "bhū": {"gana": "1", "pada": "P", "settva": "S"},
        "kṛ": {"gana": "8", "pada": "U", "settva": "A"},
    })
    
    # Load from dynamic JSON database if available
    if dhatu_filepath and os.path.exists(dhatu_filepath):
        try:
            from indic_transliteration import sanscript
        except ImportError:
            print("Warning: indic_transliteration not installed. Dhatus will not be loaded.")
            return

        with open(dhatu_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Assuming 'data' contains an array of dhatu objects from Ashtadhyayi-data
            dhatu_list = data.get("data", [])
            max_id = max(ROOT_VOCAB.values()) if ROOT_VOCAB else 0
            
            for item in dhatu_list:
                d_name_devanagari = item.get("dhatu")
                aupadeshik_dev = item.get("aupadeshik", "")
                
                if d_name_devanagari:
                    # Translate traditional Devanagari to phonetic IAST so tensor maths works
                    d_name_iast = sanscript.transliterate(d_name_devanagari, sanscript.DEVANAGARI, sanscript.IAST)
                    aupadeshik_iast = sanscript.transliterate(aupadeshik_dev, sanscript.DEVANAGARI, sanscript.IAST) if aupadeshik_dev else d_name_iast
                    
                    if d_name_iast not in ROOT_VOCAB:
                        max_id += 1
                        ROOT_VOCAB[d_name_iast] = max_id
                    ROOT_VOCAB[d_name_devanagari] = ROOT_VOCAB[d_name_iast]
                    
                    # True Paninian Anubandha Stripping
                    # ñit (ñ) -> Ubhayapada
                    # ṅit (ṅ) -> Atmanepada
                    if aupadeshik_iast.endswith("ñ"):
                        calc_pada = "U"
                    elif aupadeshik_iast.endswith("ṅ"):
                        calc_pada = "A"
                    else:
                        calc_pada = item.get("pada", "P") # Fallback
                        
                    DHATU_META[d_name_iast] = {
                        "gana": item.get("gana", "1"),
                        "pada": calc_pada,
                        "settva": item.get("settva", "S") # 'S' = seṭ, 'A' = aniṭ
                    }
                    DHATU_META[d_name_devanagari] = DHATU_META[d_name_iast]
                    
    # Generate Reverse Index mapping ID -> IAST string
    REV_ROOT.clear()
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
