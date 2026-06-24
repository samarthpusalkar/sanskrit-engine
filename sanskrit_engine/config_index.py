import json
import os

# Base Vocabulary (Dynamic)
ROOT_VOCAB = {}
REV_ROOT = {}

POS_VOCAB = {
    "noun": 1,
    "verb": 2,
    "prefix": 3,
    "sandhi_modifier": 4,
    "samasa_component": 5
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

def populate_vocabularies(dhatu_filepath: str = None):
    """
    Dynamically loads the massive Dhatupatha (and opaque nouns) into the ROOT_VOCAB.
    """
    global ROOT_VOCAB, REV_ROOT
    
    # Initialize with core test words
    ROOT_VOCAB.update({
        "gam": 1, "han": 2, "dā": 3, "bhū": 4, 
        "rāma": 5, "deva": 6, "avatāra": 7, "kṛ": 8
    })
    
    # Load from dynamic JSON database if available
    if dhatu_filepath and os.path.exists(dhatu_filepath):
        with open(dhatu_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Assuming 'data' contains an array of dhatu objects from Ashtadhyayi-data
            dhatu_list = data.get("data", [])
            max_id = max(ROOT_VOCAB.values()) if ROOT_VOCAB else 0
            
            for item in dhatu_list:
                d_name = item.get("dhatu")
                if d_name and d_name not in ROOT_VOCAB:
                    max_id += 1
                    ROOT_VOCAB[d_name] = max_id
                    
    # Generate Reverse Index
    REV_ROOT = {v: k for k, v in ROOT_VOCAB.items()}

# Initial population using static defaults
populate_vocabularies()

# Reverse Vocabularies for Decoding
REV_POS = {v: k for k, v in POS_VOCAB.items()}
REV_TENSE = {v: k for k, v in TENSE_VOCAB.items()}
REV_PERSON = {v: k for k, v in PERSON_VOCAB.items()}
REV_NUMBER = {v: k for k, v in NUMBER_VOCAB.items()}
REV_CASE = {v: k for k, v in CASE_VOCAB.items()}
REV_GENDER = {v: k for k, v in GENDER_VOCAB.items()}
