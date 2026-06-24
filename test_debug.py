from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *
from sanskrit_engine.rule_database import RuleDatabase

populate_vocabularies("data/dhatu_data.json")
rule_db = RuleDatabase("data/ashtadhyayi_db.json")
tokenizer = TensorTokenizer(RuleBasedMorphology([]), rule_db)

vec = [0, ROOT_VOCAB.get("ram", 904), 2, 1, 1, 1]
print("Vec:", vec)
coord1 = TensorCoordinate(vec)

try:
    decoded = tokenizer.decode([coord1])
    print("Decoded:", decoded)
except Exception as e:
    import traceback
    traceback.print_exc()
