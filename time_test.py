import time
from sanskrit_engine.tensor_tokenizer import TensorTokenizer
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.rule_database import RuleDatabase
from sanskrit_engine.config_index import populate_vocabularies

populate_vocabularies("data/dhatu_data.json")

print("Building tokenizer with FULL root cache...")
start = time.time()
db = RuleDatabase("data/full_demo_db.json")
tokenizer = TensorTokenizer(RuleBasedMorphology([]), db)
print(f"Time taken: {time.time() - start:.2f} seconds")
print(f"Cache size: {len(tokenizer.encode_cache)} entries")
