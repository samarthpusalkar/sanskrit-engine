from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *
from sanskrit_engine.rule_database import RuleDatabase

populate_vocabularies("data/dhatu_data.json")

# Point to empty database to test core engine first without LLM rule interference
rule_db = RuleDatabase("empty_db.json")
tokenizer = TensorTokenizer(RuleBasedMorphology([]), rule_db)

# Base Verb (ram -> ramati)
# [0, 904, 0, 2, 1, 1, 1]
c_verb = TensorCoordinate([0, ROOT_VOCAB.get("ram", 904), 0, 2, 1, 1, 1])
print("Base Verb (ramati):", tokenizer.decode([c_verb]))

# Derived Noun (ram + ghañ -> rāma)
# [0, 904, 1, 1, 1, 1, 1] (Nom Sing)
c_noun = TensorCoordinate([0, ROOT_VOCAB.get("ram", 904), 1, 1, 1, 1, 1])
print("Derived Noun (rāmasu):", tokenizer.decode([c_noun]))

# Derived Noun Genitive (ram + ghañ -> rāmasya [Base: rāmaṅas])
# [0, 904, 1, 1, 1, 6, 1]
c_noun_gen = TensorCoordinate([0, ROOT_VOCAB.get("ram", 904), 1, 1, 1, 6, 1])
print("Derived Noun Genitive (rāmaṅas):", tokenizer.decode([c_noun_gen]))

# Derived Avyaya (gam + ktvā -> gatvā)
# [0, 1, 3, 6, 0, 0, 0]
c_avyaya = TensorCoordinate([0, ROOT_VOCAB.get("gam", 1), 3, 6, 0, 0, 0])
print("Derived Avyaya (gatvā):", tokenizer.decode([c_avyaya]))

