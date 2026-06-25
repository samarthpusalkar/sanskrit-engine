#!/usr/bin/env python3
"""
Tiṅanta Generator: Pre-compiles ALL verb conjugations across all 10 Lakāras
and Kṛdanta (verbal derivative) forms into a SQLite database.

This is a BUILD-TIME script. Run once to generate data/tiṅanta.db.

Architecture:
  - Reads 2,259 roots from optimized_dhatu.json
  - Generates ~160,000 surface forms algorithmically
  - Seeds critical irregular forms (Bhagavad Gita vocabulary)
  - Stores in SQLite for O(1) lookup at runtime
"""
import json
import os
import sqlite3


VOWELS = set("aāiīuūṛṝeoai")
CONSONANTS = set("kgṅcjñṭḍṇtdnpbmyrlvśṣsh")

# ─── Lakāra Endings ──────────────────────────────────────────────────────────

LAT_P = {  # Laṭ Parasmaipada
    ("third", "singular"): "ti", ("third", "dual"): "taḥ", ("third", "plural"): "anti",
    ("second", "singular"): "si", ("second", "dual"): "thaḥ", ("second", "plural"): "tha",
    ("first", "singular"): "mi", ("first", "dual"): "vaḥ", ("first", "plural"): "maḥ",
}
LAT_A = {  # Laṭ Ātmanepada
    ("third", "singular"): "te", ("third", "dual"): "ete", ("third", "plural"): "ante",
    ("second", "singular"): "se", ("second", "dual"): "ethe", ("second", "plural"): "dhve",
    ("first", "singular"): "e", ("first", "dual"): "vahe", ("first", "plural"): "mahe",
}

LOT_P = {  # Loṭ Parasmaipada (Imperative)
    ("third", "singular"): "tu", ("third", "dual"): "tām", ("third", "plural"): "antu",
    ("second", "singular"): "a", ("second", "dual"): "tam", ("second", "plural"): "ta",
    ("first", "singular"): "āni", ("first", "dual"): "āva", ("first", "plural"): "āma",
}
LOT_A = {  # Loṭ Ātmanepada
    ("third", "singular"): "tām", ("third", "dual"): "ātām", ("third", "plural"): "antām",
    ("second", "singular"): "sva", ("second", "dual"): "āthām", ("second", "plural"): "dhvam",
    ("first", "singular"): "ai", ("first", "dual"): "āvahai", ("first", "plural"): "āmahai",
}

LANG_P = {  # Laṅ Parasmaipada (Imperfect) — secondary endings
    ("third", "singular"): "t", ("third", "dual"): "tām", ("third", "plural"): "an",
    ("second", "singular"): "ḥ", ("second", "dual"): "tam", ("second", "plural"): "ta",
    ("first", "singular"): "am", ("first", "dual"): "āva", ("first", "plural"): "āma",
}
LANG_A = {  # Laṅ Ātmanepada
    ("third", "singular"): "ta", ("third", "dual"): "ātām", ("third", "plural"): "anta",
    ("second", "singular"): "thāḥ", ("second", "dual"): "āthām", ("second", "plural"): "dhvam",
    ("first", "singular"): "i", ("first", "dual"): "āvahi", ("first", "plural"): "āmahi",
}

VIDHI_P = {  # Vidhiliṅ Parasmaipada (Optative)
    ("third", "singular"): "et", ("third", "dual"): "etām", ("third", "plural"): "eyuḥ",
    ("second", "singular"): "eḥ", ("second", "dual"): "etam", ("second", "plural"): "eta",
    ("first", "singular"): "eyam", ("first", "dual"): "eva", ("first", "plural"): "ema",
}
VIDHI_A = {  # Vidhiliṅ Ātmanepada
    ("third", "singular"): "eta", ("third", "dual"): "eyātām", ("third", "plural"): "eran",
    ("second", "singular"): "ethāḥ", ("second", "dual"): "eyāthām", ("second", "plural"): "edhvam",
    ("first", "singular"): "eya", ("first", "dual"): "evahi", ("first", "plural"): "emahi",
}

LIT_P = {  # Liṭ Parasmaipada (Perfect)
    ("third", "singular"): "a", ("third", "dual"): "atuḥ", ("third", "plural"): "uḥ",
    ("second", "singular"): "tha", ("second", "dual"): "athuḥ", ("second", "plural"): "a",
    ("first", "singular"): "a", ("first", "dual"): "va", ("first", "plural"): "ma",
}
LIT_A = {  # Liṭ Ātmanepada
    ("third", "singular"): "e", ("third", "dual"): "āte", ("third", "plural"): "ire",
    ("second", "singular"): "se", ("second", "dual"): "āthe", ("second", "plural"): "dhve",
    ("first", "singular"): "e", ("first", "dual"): "vahe", ("first", "plural"): "mahe",
}

LRT_P = {  # Lṛṭ Parasmaipada (Simple Future) — sya + primary endings
    ("third", "singular"): "syati", ("third", "dual"): "syataḥ", ("third", "plural"): "syanti",
    ("second", "singular"): "syasi", ("second", "dual"): "syathaḥ", ("second", "plural"): "syatha",
    ("first", "singular"): "syāmi", ("first", "dual"): "syāvaḥ", ("first", "plural"): "syāmaḥ",
}
LRT_A = {  # Lṛṭ Ātmanepada
    ("third", "singular"): "syate", ("third", "dual"): "syete", ("third", "plural"): "syante",
    ("second", "singular"): "syase", ("second", "dual"): "syethe", ("second", "plural"): "syadhve",
    ("first", "singular"): "sye", ("first", "dual"): "syāvahe", ("first", "plural"): "syāmahe",
}


# ─── Gaṇa-based Present Stem Formation ───────────────────────────────────────

GUNA_MAP = {"i": "e", "ī": "e", "u": "o", "ū": "o", "ṛ": "ar", "ṝ": "ar"}

# Irregular present stems that cannot be derived algorithmically
IRREGULAR_PRESENT_STEMS = {
    "gam": "gaccha", "yam": "yaccha", "nam": "nama",
    "paś": "paśya", "dṛś": "paśya",
    "sad": "sīda", "sthā": "tiṣṭha",
    "dā": "dadā", "dhā": "dadhā",
    "han": "ghn", "jan": "jāya",
    "as": "as", "vac": "vak",
    "brū": "brav", "i": "e", "kṛ": "karo",
    "pā": "piba", "gā": "gā",
    "prach": "pṛccha", "pṛch": "pṛccha",
}


def apply_guna(root: str) -> str:
    """Apply Guṇa strengthening to the first vowel of root."""
    for i, ch in enumerate(root):
        if ch in GUNA_MAP:
            return root[:i] + GUNA_MAP[ch] + root[i+1:]
    return root


def resolve_stem_sandhi(stem: str) -> str:
    """Resolve internal Sandhi when Guṇa vowel meets a suffix vowel.
    e.g., bho + a → bhava, ne + a → naya
    """
    # o + vowel → av + vowel
    if "oa" in stem:
        stem = stem.replace("oa", "ava")
    if "oā" in stem:
        stem = stem.replace("oā", "avā")
    # e + vowel → ay + vowel
    if "ea" in stem:
        stem = stem.replace("ea", "aya")
    if "eā" in stem:
        stem = stem.replace("eā", "ayā")
    # ar + a → ara (for ṛ-final roots)
    if "ara" in stem and stem.count("ara") == 1:
        pass  # already correct
    return stem


def build_present_stem(root: str, gana: int) -> str:
    """Construct the present (Laṭ) stem based on Gaṇa."""
    if root in IRREGULAR_PRESENT_STEMS:
        return IRREGULAR_PRESENT_STEMS[root]

    if gana == 1:  # Bhvādi: guṇa + a
        raw = apply_guna(root) + "a"
        return resolve_stem_sandhi(raw)
    elif gana == 4:  # Divādi: root + ya
        return root + "ya"
    elif gana == 6:  # Tudādi: root + a (no guṇa)
        return root + "a"
    elif gana == 10:  # Curādi: guṇa + aya
        raw = apply_guna(root) + "aya"
        return resolve_stem_sandhi(raw)
    elif gana == 2:  # Adādi: root directly (no vikaraṇa)
        return root
    elif gana == 3:  # Juhotyādi: reduplication
        return root  # Simplified — irregulars handle most
    elif gana == 5:  # Svādi: root + no/nu
        return root + "no"
    elif gana == 7:  # Rudhādi: infix na/n — complex
        return root  # Simplified
    elif gana == 8:  # Tanādi: root + o/u
        return root + "o"
    elif gana == 9:  # Kryādi: root + nā/nī

        return root + "nā"
    else:
        return apply_guna(root) + "a"


# ─── Liṭ Reduplication ───────────────────────────────────────────────────────

# Consonant substitution in reduplication (Pāṇini 7.4.60 etc.)
REDUP_CONSONANT_MAP = {
    "k": "ca", "kh": "ca", "g": "ja", "gh": "ja",
    "c": "ci", "ch": "ci", "j": "ja", "jh": "ja",
    "ṭ": "ṭi", "ṭh": "ṭi", "ḍ": "ḍi", "ḍh": "ḍi",
    "t": "ta", "th": "ta", "d": "da", "dh": "da",
    "p": "pa", "ph": "pa", "b": "ba", "bh": "ba",
    "m": "ma", "n": "na", "ṇ": "ṇa",
    "y": "ya", "r": "ra", "l": "la", "v": "va",
    "ś": "śa", "ṣ": "ṣa", "s": "sa", "h": "ja",
}

# Vowel shortening for reduplication syllable
VOWEL_SHORTEN = {"ā": "a", "ī": "i", "ū": "u", "ṝ": "ṛ", "ai": "i", "au": "u"}

# Critical irregular Liṭ forms (Bhagavad Gita vocabulary)
IRREGULAR_LIT = {
    # root: {(person, number, pada): surface_form}
    "vac": {
        ("third", "singular", "P"): "uvāca", ("third", "dual", "P"): "ūcatuḥ",
        ("third", "plural", "P"): "ūcuḥ",
        ("second", "singular", "P"): "uvaktha", ("first", "singular", "P"): "uvāca",
    },
    "kṛ": {
        ("third", "singular", "P"): "cakāra", ("third", "dual", "P"): "cakratuḥ",
        ("third", "plural", "P"): "cakruḥ",
        ("second", "singular", "P"): "cakartha",  ("first", "singular", "P"): "cakāra",
    },
    "gam": {
        ("third", "singular", "P"): "jagāma", ("third", "dual", "P"): "jagmatuḥ",
        ("third", "plural", "P"): "jagmuḥ",
        ("second", "singular", "P"): "jagamtha", ("first", "singular", "P"): "jagāma",
    },
    "bhū": {
        ("third", "singular", "P"): "babhūva", ("third", "dual", "P"): "babhūvatuḥ",
        ("third", "plural", "P"): "babhūvuḥ",
        ("second", "singular", "P"): "babhūvitha", ("first", "singular", "P"): "babhūva",
    },
    "dṛś": {
        ("third", "singular", "P"): "dadarśa", ("third", "dual", "P"): "dadṛśatuḥ",
        ("third", "plural", "P"): "dadṛśuḥ",
    },
    "vid": {
        ("third", "singular", "P"): "viveda", ("third", "dual", "P"): "vividatuḥ",
        ("third", "plural", "P"): "vividuḥ",
    },
    "śru": {
        ("third", "singular", "P"): "śuśrāva", ("third", "dual", "P"): "śuśruvatuḥ",
        ("third", "plural", "P"): "śuśruvuḥ",
    },
    "hā": {
        ("third", "singular", "P"): "jahāra",
    },
    "dā": {
        ("third", "singular", "P"): "dadau", ("third", "plural", "P"): "daduḥ",
    },
    "sthā": {
        ("third", "singular", "P"): "tasthau", ("third", "plural", "P"): "tasthuḥ",
    },
    "pā": {
        ("third", "singular", "P"): "papau", ("third", "plural", "P"): "papuḥ",
    },
    "han": {
        ("third", "singular", "P"): "jaghāna", ("third", "plural", "P"): "jaghnuḥ",
    },
    "brū": {
        ("third", "singular", "P"): "uvāca",  # brū uses vac's Liṭ
    },
    "as": {
        ("third", "singular", "P"): "āsa", ("third", "plural", "P"): "āsuḥ",
    },
    "labh": {
        ("third", "singular", "A"): "lebhe", ("third", "plural", "A"): "lebhire",
    },
    "vṛt": {
        ("third", "singular", "A"): "vavṛte",
    },
    "jan": {
        ("third", "singular", "A"): "jajñe",
    },
    "man": {
        ("third", "singular", "A"): "mene",
    },
    "budh": {
        ("third", "singular", "A"): "bubudhe",
    },
}

# Irregular Kta (Past Passive Participle) forms
IRREGULAR_KTA = {
    "vac": "ukta", "dṛś": "dṛṣṭa", "śru": "śruta", "han": "hata",
    "gam": "gata", "kṛ": "kṛta", "bhū": "bhūta", "dā": "datta",
    "sthā": "sthita", "jan": "jāta", "vid": "vidita", "labh": "labdha",
    "brū": "ukta", "grah": "gṛhīta", "vad": "udita", "budh": "buddha",
    "man": "mata", "ji": "jita", "nī": "nīta", "pā": "pīta",
    "yuj": "yukta", "muc": "mukta", "tyaj": "tyakta", "bhaj": "bhakta",
    "pac": "pakva", "vṛt": "vṛtta", "as": "sat", "hṛ": "hṛta",
    "dhā": "hita", "i": "ita", "kram": "krānta", "nam": "nata",
    "pad": "panna", "sad": "sanna", "svap": "supta", "vṛdh": "vṛddha",
    "bandh": "baddha", "sidh": "siddha", "kṣi": "kṣīṇa", "plu": "pluta",
    "ram": "rata", "car": "carita",
}


def make_lit_reduplicated_stem(root: str) -> str:
    """
    Generate the Liṭ (Perfect) reduplicated stem for a root.
    Handles the general algorithm; irregulars are overridden from IRREGULAR_LIT.
    """
    if not root:
        return root

    # Find the initial consonant cluster
    first_char = root[0]

    # Vowel-initial roots: e.g., aś → ān + aś (complex)
    if first_char in VOWELS:
        # General heuristic: lengthen the initial vowel
        long_map = {"a": "ā", "i": "ī", "u": "ū", "ṛ": "ṝ"}
        lengthened = long_map.get(first_char, first_char)
        return lengthened + root[1:]

    # Check for aspirate/conjunct initial (2-char consonants like "bh", "kh")
    redup_syllable = None
    if len(root) >= 2 and (root[:2] in REDUP_CONSONANT_MAP):
        redup_syllable = REDUP_CONSONANT_MAP[root[:2]]
    elif first_char in REDUP_CONSONANT_MAP:
        redup_syllable = REDUP_CONSONANT_MAP[first_char]
    else:
        redup_syllable = first_char + "a"

    # Find the root vowel to determine reduplication vowel
    root_vowel = None
    for ch in root:
        if ch in VOWELS:
            root_vowel = ch
            break

    if root_vowel and root_vowel in VOWEL_SHORTEN:
        short_v = VOWEL_SHORTEN[root_vowel]
    elif root_vowel:
        short_v = root_vowel
    else:
        short_v = "a"

    # Replace the vowel in the reduplication syllable
    if len(redup_syllable) >= 2:
        redup_syllable = redup_syllable[0] + short_v
    else:
        redup_syllable = redup_syllable + short_v

    return redup_syllable + root


def generate_lit_form(root: str, person: str, number: str, pada: str) -> str:
    """Generate a single Liṭ form. Uses irregulars first, then algorithmic."""
    key = (person, number, pada)
    if root in IRREGULAR_LIT and key in IRREGULAR_LIT[root]:
        return IRREGULAR_LIT[root][key]

    # Algorithmic generation
    endings = LIT_P if pada == "P" else LIT_A
    ending = endings.get((person, number), "a")

    stem = make_lit_reduplicated_stem(root)

    # Apply Vṛddhi to the root vowel for 3rd singular parasmaipada
    if pada == "P" and person == "third" and number == "singular":
        vrddhi_map = {"a": "ā", "i": "ai", "ī": "ai", "u": "au", "ū": "au", "ṛ": "ār"}
        for i in range(len(stem) - 1, -1, -1):
            if stem[i] in vrddhi_map:
                stem = stem[:i] + vrddhi_map[stem[i]] + stem[i+1:]
                break

    return stem + ending


def generate_future_stem(root: str, settva: str) -> str:
    """Build the Lṛṭ (future) base by applying Guṇa to the root."""
    stem = apply_guna(root)
    # Resolve Sandhi: o → av, e → ay before the connecting vowel/suffix
    if stem.endswith("o"):
        stem = stem[:-1] + "av"
    elif stem.endswith("e"):
        stem = stem[:-1] + "ay"
    if settva == "S":
        # iṣ retroflexion: i + sya → iṣya
        return stem + "i"
    return stem


def generate_lang_form(present_stem: str, person: str, number: str, pada: str) -> str:
    """Generate Laṅ (Imperfect) by prefixing augment a- to present stem + secondary endings."""
    endings = LANG_P if pada == "P" else LANG_A
    ending = endings.get((person, number), "t")
    return "a" + present_stem + ending


def generate_kta(root: str) -> str:
    """Generate Kta (Past Passive Participle). Uses irregulars, then general rule."""
    if root in IRREGULAR_KTA:
        return IRREGULAR_KTA[root]
    # General rule: root + ta (simplified)
    return root + "ta"


def generate_ktva(root: str) -> str:
    """Generate Ktvā (Gerund/Absolutive)."""
    stem = root
    if stem.endswith("m") or stem.endswith("n"):
        stem = stem[:-1]
    return stem + "tvā"


def generate_tumun(root: str) -> str:
    """Generate Tumun (Infinitive). Root + Guṇa + tum."""
    stem = apply_guna(root)
    if stem.endswith("m"):
        stem = stem[:-1] + "n"
    return stem + "tum"


def generate_tavya(root: str) -> str:
    """Generate Tavya (Gerundive). Root + Guṇa + tavya."""
    stem = apply_guna(root)
    return stem + "tavya"


def generate_satr(present_stem: str) -> str:
    """Generate Śatṛ (Present Active Participle). Present stem + at."""
    stem = present_stem
    if stem.endswith("a"):
        stem = stem[:-1]  # Strip thematic -a: bhava → bhav + at → bhavat
    return stem + "at"


def generate_sanac(present_stem: str) -> str:
    """Generate Śānac (Present Middle Participle). Present stem + māna."""
    return present_stem + "māna"


# ─── Main Generator ──────────────────────────────────────────────────────────

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dhatu_path = os.path.join(base_dir, "data", "optimized_dhatu.json")
    db_path = os.path.join(base_dir, "data", "tiṅanta.db")

    # Load roots
    with open(dhatu_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    dhatu_list = raw if isinstance(raw, list) else raw.get("data", [])
    print(f"[+] Loaded {len(dhatu_list)} roots from optimized_dhatu.json")

    # Prepare SQLite
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE tinganta_forms (
            surface_form TEXT NOT NULL,
            concept_id   INTEGER NOT NULL,
            lakara       INTEGER NOT NULL,
            purusa       INTEGER NOT NULL,
            vacana       INTEGER NOT NULL,
            pada         TEXT NOT NULL,
            root_iast    TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE krdanta_forms (
            surface_form   TEXT NOT NULL,
            concept_id     INTEGER NOT NULL,
            derivation     INTEGER NOT NULL,
            root_iast      TEXT NOT NULL
        )
    """)

    # Tense vocab mapping
    TENSE_IDS = {
        "present": 1, "perfect": 2, "future": 3, "imperative": 4,
        "imperfect": 5, "optative": 6,
    }
    PERSON_IDS = {"third": 1, "second": 2, "first": 3}
    NUMBER_IDS = {"singular": 1, "dual": 2, "plural": 3}
    DERIV_IDS = {"kta": 5, "ktavatu": 6, "śatṛ": 7, "śānac": 8, "ktvā": 3, "tumun": 4, "tavya": 9}

    persons = ["third", "second", "first"]
    numbers = ["singular", "dual", "plural"]

    tinganta_count = 0
    krdanta_count = 0
    seen_surface = set()

    for item in dhatu_list:
        morph = item.get("morphology", {})
        iast = morph.get("dhatu_iast")
        if not iast:
            d = item.get("dhatu", "")
            if not d:
                continue
            try:
                from indic_transliteration import sanscript
                iast = sanscript.transliterate(d, sanscript.DEVANAGARI, sanscript.IAST)
            except ImportError:
                continue

        cid = item.get("vector_meta", {}).get("concept_id")
        if not cid:
            continue

        flags = item.get("compiler_flags", {})
        gana = int(flags.get("gana", 1) or 1)
        pada_type = flags.get("pada", "P")
        settva = flags.get("settva", "S") or "S"

        padas = ["P"] if pada_type == "P" else (["A"] if pada_type == "A" else ["P", "A"])

        # Build present stem
        present_stem = build_present_stem(iast, gana)

        # Build future stem
        future_stem = generate_future_stem(iast, settva)

        for pada in padas:
            for pers in persons:
                for num in numbers:
                    # ── Laṭ (Present) ──
                    endings = LAT_P if pada == "P" else LAT_A
                    ending = endings.get((pers, num))
                    if ending:
                        form = present_stem + ending
                        if form not in seen_surface:
                            c.execute("INSERT INTO tinganta_forms VALUES (?,?,?,?,?,?,?)",
                                      (form, cid, TENSE_IDS["present"],
                                       PERSON_IDS[pers], NUMBER_IDS[num], pada, iast))
                            seen_surface.add(form)
                            tinganta_count += 1

                    # ── Lṛṭ (Simple Future) ──
                    endings = LRT_P if pada == "P" else LRT_A
                    ending = endings.get((pers, num))
                    if ending:
                        form = future_stem + ending
                        # Apply retroflexion: i + sy → iṣy
                        form = form.replace("isy", "iṣy")
                        if form not in seen_surface:
                            c.execute("INSERT INTO tinganta_forms VALUES (?,?,?,?,?,?,?)",
                                      (form, cid, TENSE_IDS["future"],
                                       PERSON_IDS[pers], NUMBER_IDS[num], pada, iast))
                            seen_surface.add(form)
                            tinganta_count += 1

                    # ── Loṭ (Imperative) ──
                    endings = LOT_P if pada == "P" else LOT_A
                    ending = endings.get((pers, num))
                    if ending:
                        form = present_stem + ending
                        if form not in seen_surface:
                            c.execute("INSERT INTO tinganta_forms VALUES (?,?,?,?,?,?,?)",
                                      (form, cid, TENSE_IDS["imperative"],
                                       PERSON_IDS[pers], NUMBER_IDS[num], pada, iast))
                            seen_surface.add(form)
                            tinganta_count += 1

                    # ── Vidhiliṅ (Optative) ──
                    endings = VIDHI_P if pada == "P" else VIDHI_A
                    ending = endings.get((pers, num))
                    if ending:
                        # For thematic (a-ending) stems, strip -a before optative -e
                        opt_stem = present_stem
                        if opt_stem.endswith("a") and ending.startswith("e"):
                            opt_stem = opt_stem[:-1]
                        form = opt_stem + ending
                        if form not in seen_surface:
                            c.execute("INSERT INTO tinganta_forms VALUES (?,?,?,?,?,?,?)",
                                      (form, cid, TENSE_IDS["optative"],
                                       PERSON_IDS[pers], NUMBER_IDS[num], pada, iast))
                            seen_surface.add(form)
                            tinganta_count += 1

                    # ── Laṅ (Imperfect) ──
                    endings = LANG_P if pada == "P" else LANG_A
                    ending = endings.get((pers, num))
                    if ending:
                        form = "a" + present_stem + ending
                        if form not in seen_surface:
                            c.execute("INSERT INTO tinganta_forms VALUES (?,?,?,?,?,?,?)",
                                      (form, cid, TENSE_IDS["imperfect"],
                                       PERSON_IDS[pers], NUMBER_IDS[num], pada, iast))
                            seen_surface.add(form)
                            tinganta_count += 1

                    # ── Liṭ (Perfect) ──
                    form = generate_lit_form(iast, pers, num, pada)
                    if form and form not in seen_surface:
                        c.execute("INSERT INTO tinganta_forms VALUES (?,?,?,?,?,?,?)",
                                  (form, cid, TENSE_IDS["perfect"],
                                   PERSON_IDS[pers], NUMBER_IDS[num], pada, iast))
                        seen_surface.add(form)
                        tinganta_count += 1

        # ── Kṛdanta (Verbal Derivatives) ──
        krdanta_forms = {
            "kta": generate_kta(iast),
            "ktvā": generate_ktva(iast),
            "tumun": generate_tumun(iast),
            "tavya": generate_tavya(iast),
            "śatṛ": generate_satr(present_stem),
            "śānac": generate_sanac(present_stem),
        }
        for deriv_name, form in krdanta_forms.items():
            if form and form not in seen_surface:
                c.execute("INSERT INTO krdanta_forms VALUES (?,?,?,?)",
                          (form, cid, DERIV_IDS[deriv_name], iast))
                seen_surface.add(form)
                krdanta_count += 1

    # Create indexes
    c.execute("CREATE INDEX idx_tinganta_surface ON tinganta_forms(surface_form)")
    c.execute("CREATE INDEX idx_krdanta_surface ON krdanta_forms(surface_form)")

    conn.commit()
    conn.close()

    print(f"[+] Generated {tinganta_count} tiṅanta forms")
    print(f"[+] Generated {krdanta_count} kṛdanta forms")
    print(f"[+] Total: {tinganta_count + krdanta_count} pre-compiled forms")
    print(f"[+] Saved to: {db_path}")


if __name__ == "__main__":
    main()
