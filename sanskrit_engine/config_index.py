"""
Vocabulary configuration mapping strings to numerical IDs for the Tensor Tokenizer.
"""

ROOT_VOCAB = {
    "gam": 1,
    "han": 2,
    "dā": 3,
    "bhū": 4,
    "rāma": 5,
    "deva": 6,
    "avatāra": 7,
    "kṛ": 8
}

POS_VOCAB = {
    "noun": 1,
    "verb": 2,
    "prefix": 3,
    "sandhi_modifier": 4
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

# Reverse Vocabularies for Decoding
REV_ROOT = {v: k for k, v in ROOT_VOCAB.items()}
REV_POS = {v: k for k, v in POS_VOCAB.items()}
REV_TENSE = {v: k for k, v in TENSE_VOCAB.items()}
REV_PERSON = {v: k for k, v in PERSON_VOCAB.items()}
REV_NUMBER = {v: k for k, v in NUMBER_VOCAB.items()}
REV_CASE = {v: k for k, v in CASE_VOCAB.items()}
REV_GENDER = {v: k for k, v in GENDER_VOCAB.items()}
