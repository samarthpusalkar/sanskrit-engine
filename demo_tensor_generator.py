import sys
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine import load_rules
from sanskrit_engine.config_index import *

def print_vocab():
    print("\n--- Available Vocabulary (v0.2 Demo) ---")
    print(f"Roots: {ROOT_VOCAB}")
    print(f"POS: {POS_VOCAB}")
    print(f"Tense: {TENSE_VOCAB}")
    print(f"Person: {PERSON_VOCAB}")
    print(f"Number: {NUMBER_VOCAB}")
    print(f"Gender: {GENDER_VOCAB}")
    print(f"Case: {CASE_VOCAB}")
    print("----------------------------------------\n")

def main():
    print("Initializing Sanskrit Tensor Engine...")
    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(rules)
    tokenizer = TensorTokenizer(morphology)
    
    print("Engine Ready!")
    
    while True:
        print("\nOptions:")
        print("1. Enter an Integer Vector (e.g. [1, 2, 1, 1, 1])")
        print("2. Enter a String to Encode (e.g. 'rāmaḥ gacchati' or 'dadāti')")
        print("3. View Vocabulary Index")
        print("4. Exit")
        
        choice = input("Select an option: ").strip()
        
        if choice == "4":
            break
        elif choice == "3":
            print_vocab()
        elif choice == "2":
            text = input("Enter phrase: ").strip()
            encoded = tokenizer.encode(text)
            if not encoded:
                print("Error: Demo encoder only supports predefined exact phrases ('rāmaḥ gacchati', 'dadāti', 'jaghāna').")
            else:
                for coord in encoded:
                    print(f"Vector Token -> {coord.vector}")
        elif choice == "1":
            vec_input = input("Enter 5 integers separated by space (Root, POS, Feat1, Feat2, Feat3): ").strip()
            try:
                vec = [int(x) for x in vec_input.split()]
                if len(vec) != 5:
                    print("Error: Must provide exactly 5 integers.")
                    continue
                coord = TensorCoordinate(vec)
                word = tokenizer.decode([coord])
                print(f"\n=> Generated Word: {word}")
            except Exception as e:
                print(f"Error parsing input: {e}")

if __name__ == "__main__":
    main()
