import os
import json
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.rule_database import RuleDatabase
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *
from sanskrit_engine import load_rules

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def setup_engine():
    # 1. Load Vocabularies dynamically
    if os.path.exists("data/dhatu_data.json"):
        populate_vocabularies("data/dhatu_data.json")

    # 2. Setup Database
    db_path = "data/full_demo_db.json"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = RuleDatabase(db_path)
    
    # 3. Insert specific transformation rules (Panini exceptions)
    rules_to_insert = [
        {
            "rule_id": "P. 6.1.8 (bhu_perfect)",
            "name": "Bhu Perfect Reduplication",
            "category": "vidhi", "priority": 100, "domain": ["verb"],
            "operation": {
                "type": "lambda",
                "executable": "lambda token, env: {'pos': token['pos'], 'text': 'babhūva', 'applied_rules': token.get('applied_rules', []) + ['P. 6.1.8 (Liti Dhatur Anabhyasasya)']} if env.get('root') == 'bhū' and env.get('tense') == 'perfect' else token"
            }
        },
        {
            "rule_id": "P. 7.3.54 (han_plural_shift)",
            "name": "Han Plural Consonant Shift",
            "category": "vidhi", "priority": 100, "domain": ["verb"],
            "operation": {
                "type": "lambda",
                "executable": "lambda token, env: {'pos': token['pos'], 'text': 'ghnanti', 'applied_rules': token.get('applied_rules', []) + ['P. 7.3.54 (Ho Hante Nninesu)']} if env.get('root') == 'han' and env.get('tense') == 'present' and env.get('number') == 'plural' else token"
            }
        }
    ]
    for r in rules_to_insert:
        db.insert_rule(r)

    # 4. Setup Morphology and Tokenizer
    morph_rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(morph_rules)
    return TensorTokenizer(morphology, rule_db=db)

def print_header():
    print("==========================================================")
    print("   Sanskrit Tensor Engine: Full Architecture Demo")
    print("==========================================================")

def demo_encode(tokenizer):
    print("\n--- 1. ENCODING SANSKRIT TO TENSORS ---")
    sentence = "rāmaḥ gacchati"
    print(f"Input Sentence: '{sentence}'")
    
    tensors = tokenizer.encode(sentence)
    print("\nGenerated Tensors:")
    for i, t in enumerate(tensors):
        print(f"  Word {i+1}: {t.vector}")
    
    print("\nUnder the hood:")
    print("  Word 1: [Root: rāma(5), POS: noun(1), Gender: masc(1), Case: nom(1), Number: sing(1)]")
    print("  Word 2: [Root: gam(1),  POS: verb(2), Tense: present(1), Person: 3rd(1), Number: sing(1)]")
    input("\nPress Enter to continue...")

def demo_algebra(tokenizer):
    print("\n--- 2. TENSOR MATRIX SURGERY & DECODING ---")
    print("You can test any of the 1,700+ Dhatus dynamically!")
    
    user_root = input("Enter a root word in IAST (e.g., bhū, gam, dā, i, kṛ): ").strip()
    
    if user_root not in ROOT_VOCAB:
        print(f"Error: Root '{user_root}' not found in the Dhatu database.")
        input("\nPress Enter to return to menu...")
        return
        
    root_idx = ROOT_VOCAB[user_root]
    print(f"\nConstructing Present Tense Base Vector for '{user_root}'...")
    base = TensorCoordinate([root_idx, 2, 1, 1, 1])
    print(f"[Base Vector]:  {base.vector} -> Decodes to: {tokenizer.decode([base])}")
    
    print("\nEnter a surgical TensorDelta to apply.")
    print("Example: '0 0 1 0 0' adds +1 to Tense (Present(1) -> Perfect(2))")
    print("Example: '0 0 0 0 2' adds +2 to Number (Singular(1) -> Plural(3))")
    
    delta_input = input("Enter 5 integers separated by space: ")
    try:
        delta_vals = [int(x) for x in delta_input.split()]
        if len(delta_vals) != 5:
            raise ValueError
        delta = TensorDelta(delta_vals)
    except ValueError:
        print("Invalid delta format.")
        input("\nPress Enter to return to menu...")
        return
        
    perfect_vector = base + delta
    print(f"\n[Result Matrix]: {perfect_vector.vector}")
    
    print("\nDetokenizing mutated matrix...")
    # Map the new vector to environment variables to show what DB sees
    env = {
        "root": user_root,
        "pos": "verb",
        "tense": REV_TENSE.get(perfect_vector.vector[2], "unknown"),
        "person": REV_PERSON.get(perfect_vector.vector[3], "unknown"),
        "number": REV_NUMBER.get(perfect_vector.vector[4], "unknown")
    }
    
    # Let's show rule execution
    token = {"pos": "verb", "text": user_root, "applied_rules": []}
    rules = tokenizer.rule_db.get_applicable_rules(token, env)
    
    if len(rules) > 0:
        print(f"-> RuleDatabase matched {len(rules)} potential Paninian Exceptions for this semantic state!")
        for r in rules:
            token = r.apply(token, env)
            
            applied = token.get('applied_rules', [])
            if len(applied) > 0:
                print(f"   -> Applied matrix transformation via Panini sutra: {applied[-1]}")
    else:
        print("-> RuleDatabase matched 0 specific exceptions. Using standard base morphology.")
        
    print(f"\n[Final Output String]: {tokenizer.decode([perfect_vector])}")
    input("\nPress Enter to continue...")

def demo_pipeline():
    print("\n--- 3. LLM AUTOMATION PIPELINE (MOCKED) ---")
    print("Running the pipeline that reads natural Sanskrit text and generates JSON matrices...")
    
    sample_text = "अकः सवर्णे दीर्घः (6.1.101)"
    print(f"Input Sutra: {sample_text}")
    print("\nAgentic Loop Output:")
    
    mock_json = {
        "rule_id": "6.1.101",
        "category": "sandhi",
        "operation": "lambda token: merge_vowels(token)"
    }
    print(json.dumps(mock_json, indent=2))
    print("Status: Unit test passed. Committed to RuleDatabase.")
    input("\nPress Enter to continue...")

def demo_vocab():
    print("\n--- 4. DYNAMIC DHATU INDEXING ---")
    print(f"Total Roots (Dhatus) currently loaded into the Tensor Matrix: {len(ROOT_VOCAB)}")
    print("Examples of 1-letter atomic roots natively accessible:")
    examples = [k for k in ROOT_VOCAB.keys() if len(k) == 1]
    print(f"  {', '.join(examples[:10])} ...")
    input("\nPress Enter to continue...")

def main():
    clear_screen()
    print("Booting up Tensor Engine, loading 1,700+ Dhatus and mapping RuleDatabase...")
    tokenizer = setup_engine()
    
    while True:
        clear_screen()
        print_header()
        print("1. Encode Sentence to Tensors")
        print("2. Matrix Surgery (Tense Mutation & DB Fetch)")
        print("3. View LLM Compiler Pipeline")
        print("4. View Dhatu Tensor Index Size")
        print("5. Exit")
        
        choice = input("\nSelect a module to demo: ")
        
        if choice == '1':
            demo_encode(tokenizer)
        elif choice == '2':
            demo_algebra(tokenizer)
        elif choice == '3':
            demo_pipeline()
        elif choice == '4':
            demo_vocab()
        elif choice == '5':
            break

if __name__ == "__main__":
    main()
