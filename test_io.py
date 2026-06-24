import json
from indic_transliteration import sanscript
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import populate_vocabularies
from sanskrit_engine.rule_database import RuleDatabase

# Populate dictionary
populate_vocabularies("data/dhatu_data.json")

def main():
    print("--- Tokenizer Serialization Test ---")
    
    # 1. INITIALIZE ENCODER
    rule_db = RuleDatabase("data/full_demo_db.json")
    encoder = TensorTokenizer(RuleBasedMorphology([]), rule_db)
    
    user_input = input("Enter Sanskrit text (Devanagari or IAST): ").strip()
    
    # Auto-detect script based on character ranges
    if any("\u0900" <= c <= "\u097F" for c in user_input):
        sentence_iast = sanscript.transliterate(user_input, sanscript.DEVANAGARI, sanscript.IAST)
    else:
        sentence_iast = user_input
        
    print(f"Input (IAST): {sentence_iast}")
    
    # 2. VECTORIZE
    tensors = encoder.encode(sentence_iast)
    
    vector_data = [t.vector for t in tensors]
    print(f"Encoded Matrices: {vector_data}")
    
    # 3. STORE TO FILE
    filepath = "tensor_cache.json"
    with open(filepath, "w") as f:
        json.dump({"tensors": vector_data}, f)
    print(f"Stored matrices to '{filepath}'.")
    
    # --- Simulate new session / new machine ---
    print("\n--- Starting fresh decoder session ---")
    
    # 4. INITIALIZE NEW TOKENIZER
    new_rule_db = RuleDatabase("data/full_demo_db.json")
    decoder = TensorTokenizer(RuleBasedMorphology([]), new_rule_db)
    
    # 5. READ FROM FILE
    with open(filepath, "r") as f:
        loaded_data = json.load(f)["tensors"]
        
    loaded_tensors = [TensorCoordinate(v) for v in loaded_data]
    print(f"Loaded Matrices: {[t.vector for t in loaded_tensors]}")
    
    # 6. DECODE
    decoded_iast = decoder.decode(loaded_tensors)
    print(f"Decoded (IAST): {decoded_iast}")
    
    decoded_devanagari = sanscript.transliterate(decoded_iast, sanscript.IAST, sanscript.DEVANAGARI)
    print(f"Decoded (Devanagari): {decoded_devanagari}")

if __name__ == "__main__":
    main()
