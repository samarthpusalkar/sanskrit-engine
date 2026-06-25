import json
import os
from indic_transliteration import sanscript

def determine_ending(dhatu_dev):
    """
    Determines if the root ends in a vowel (Ajanta) or consonant (Halanta)
    and extracts the final phoneme in SLP1 for phonetic math.
    """
    # In Devanagari, a Halanta ends with the Virama character (्) - Unicode \u094d
    is_ajanta = not dhatu_dev.endswith('्')
    
    # Transliterate to SLP1 to easily grab the final ASCII phoneme
    dhatu_slp1 = sanscript.transliterate(dhatu_dev, sanscript.DEVANAGARI, sanscript.SLP1)
    final_phoneme = dhatu_slp1[-1] if dhatu_slp1 else ""
    
    return is_ajanta, final_phoneme

def parse_tags(tags_string):
    """
    Extracts the Pāṇinian accent type from the raw tags string.
    """
    if not tags_string:
        return None
        
    tags = tags_string.split(',')
    for tag in tags:
        if 'अनुदात्त' in tag:
            return 'anudatta'
        elif 'उदात्त' in tag:
            return 'udatta'
        elif 'स्वरित' in tag:
            return 'svarita'
    return None

def convert_schema(raw_item):
    """
    Maps the raw repo dictionary to the optimized LLM vector schema.
    """
    dhatu_dev = raw_item.get("dhatu", "").strip()
    aupadeshik_dev = raw_item.get("aupadeshik", "").strip()
    
    # Generate the crucial SLP1 forms for the deterministic compiler
    dhatu_iast = sanscript.transliterate(dhatu_dev, sanscript.DEVANAGARI, sanscript.IAST)
    dhatu_slp1 = sanscript.transliterate(dhatu_dev, sanscript.DEVANAGARI, sanscript.SLP1)
    aup_iast = sanscript.transliterate(aupadeshik_dev, sanscript.DEVANAGARI, sanscript.IAST)
    aup_slp1 = sanscript.transliterate(aupadeshik_dev, sanscript.DEVANAGARI, sanscript.SLP1)
    
    is_ajanta, final_phoneme = determine_ending(dhatu_dev)
    
    # Handle potentially missing or empty numeric fields
    gana_raw = raw_item.get("gana", "")
    gana_int = int(gana_raw) if str(gana_raw).isdigit() else None
    
    id_raw = raw_item.get("i", "0")
    concept_id = int(id_raw) if str(id_raw).isdigit() else 0

    return {
        "vector_meta": {
            "concept_id": concept_id,
            "baseindex": raw_item.get("baseindex", "")
        },
        "morphology": {
            "dhatu_dev": dhatu_dev,
            "dhatu_iast": dhatu_iast,
            "dhatu_slp1": dhatu_slp1,
            "aupadeshik_dev": aupadeshik_dev,
            "aupadeshik_iast": aup_iast,
            "aupadeshik_slp1": aup_slp1,
            "is_ajanta": is_ajanta,
            "final_phoneme": final_phoneme
        },
        "compiler_flags": {
            "gana": gana_int,
            "pada": raw_item.get("pada", ""),
            "settva": raw_item.get("settva", ""),
            "karma": raw_item.get("karma", ""),
            "accent_type": parse_tags(raw_item.get("tags", "")),
            "antargana": raw_item.get("antarganas", "") or None
        },
        "semantics": {
            "artha_sanskrit": raw_item.get("artha", ""),
            "artha_hindi": raw_item.get("artha_hindi", ""),
            "artha_english": raw_item.get("artha_english", ""),
            "attested_upasargas": raw_item.get("upasargas", [])
        },
        "reference_data": {
            "dhaturoopnandini_id": str(raw_item.get("dhaturoopnandini", "")),
            "sk_sutra": str(raw_item.get("sk_sutra", "")),
            "notes": raw_item.get("dhaturoopnandini_note", "")
        }
    }

def process_directory(input_file_path, output_file_path):
    """Reads the original JSON list and writes the converted list."""
    with open(input_file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    raw_data = raw_data['data']
    converted_data = [convert_schema(item) for item in raw_data]
    
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully converted {len(converted_data)} roots.")

# Example execution
process_directory('/Users/samarthpusalkar/Documents/sanskrit_engine/data/dhatu_data.json', '/Users/samarthpusalkar/Documents/sanskrit_engine/data/optimized_dhatu.json')
