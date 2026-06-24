import os
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.rule_database import RuleDatabase
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine import load_rules
from sanskrit_engine.config_index import *

def setup_demo_environment():
    """Sets up the tokenizer and seeds the DB with rules for the demo."""
    db_path = "data/demo_db.json"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = RuleDatabase(db_path)
    
    # Rule 1: Perfect tense of 'bhū' -> babhūva
    db.insert_rule({
        "rule_id": "bhu_perfect_redup",
        "priority": 100, "domain": ["verb"],
        "operation": {
            "type": "lambda",
            "executable": "lambda token, env: {'pos': token['pos'], 'text': 'babhūva'} if env.get('root') == 'bhū' and env.get('tense') == 'perfect' else token"
        }
    })
    
    # Rule 2: 'han' present plural -> ghnanti (Consonant shift Apavāda)
    db.insert_rule({
        "rule_id": "han_plural_shift",
        "priority": 100, "domain": ["verb"],
        "operation": {
            "type": "lambda",
            "executable": "lambda token, env: {'pos': token['pos'], 'text': 'ghnanti'} if env.get('root') == 'han' and env.get('tense') == 'present' and env.get('number') == 'plural' else token"
        }
    })
    
    # Rule 3: 'han' perfect singular -> jaghāna
    db.insert_rule({
        "rule_id": "han_perfect_sing",
        "priority": 100, "domain": ["verb"],
        "operation": {
            "type": "lambda",
            "executable": "lambda token, env: {'pos': token['pos'], 'text': 'jaghāna'} if env.get('root') == 'han' and env.get('tense') == 'perfect' and env.get('number') == 'singular' else token"
        }
    })

    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(rules)
    return TensorTokenizer(morphology, rule_db=db)

def interactive_demo():
    print("==================================================")
    print("   Sanskrit Tensor Algebra & DB Fetching Demo")
    print("==================================================")
    
    # Load ~1700 dhatus to memory if available
    if os.path.exists("data/dhatu_data.json"):
        populate_vocabularies("data/dhatu_data.json")
        
    tokenizer = setup_demo_environment()
    
    while True:
        print("\nOptions:")
        print("1. Custom Matrix Surgery (Tense Transformation)")
        print("2. Custom Matrix Surgery (Plurality Transformation)")
        print("3. Exit")
        
        choice = input("Select an option: ")
        
        if choice == "1":
            print("\n[Base Matrix]: root=bhū (4), verb (2), present (1), third (1), singular (1)")
            base = TensorCoordinate([4, 2, 1, 1, 1])
            print(f"Decoded Base: {tokenizer.decode([base])}")
            
            print("\n[Surgery]: We will apply TensorDelta [0, 0, +1, 0, 0] to change Tense to Perfect (2)")
            delta = TensorDelta([0, 0, 1, 0, 0])
            perfect_vector = base + delta
            print(f"Resulting Vector: {perfect_vector.vector}")
            
            print(f"Decoded Surgery: {tokenizer.decode([perfect_vector])}  <-- Fetched dynamically from RuleDB!")
            
        elif choice == "2":
            print("\n[Base Matrix]: root=han (6), verb (2), present (1), third (1), singular (1)")
            # In our mock VOCAB, let's assume 'han' might not be 6, let's fetch its actual ID
            han_id = ROOT_VOCAB.get("han", 6)
            base = TensorCoordinate([han_id, 2, 1, 1, 1])
            print(f"Decoded Base: {tokenizer.decode([base])}")
            
            print("\n[Surgery]: We will apply TensorDelta [0, 0, 0, 0, +2] to change Number to Plural (3)")
            delta = TensorDelta([0, 0, 0, 0, 2])
            plural_vector = base + delta
            print(f"Resulting Vector: {plural_vector.vector}")
            
            print(f"Decoded Surgery: {tokenizer.decode([plural_vector])}  <-- Note the consonant shift (h -> gh) applied by the DB!")
            
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    interactive_demo()
