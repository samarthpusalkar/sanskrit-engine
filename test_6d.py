from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *
from sanskrit_engine.rule_database import RuleDatabase

populate_vocabularies("data/dhatu_data.json")

# Point to empty database to test core engine first without LLM rule interference
rule_db = RuleDatabase("empty_db.json")
tokenizer = TensorTokenizer(RuleBasedMorphology([]), rule_db)

print("1. Testing gam -> gamati (Present, base morphology before RuleDB replacement to gacchati)")
# 0 (none), gam (1), 2 (verb), 1 (present), 1 (third), 1 (singular)
coord1 = TensorCoordinate([0, ROOT_VOCAB.get("gam", 1), 2, 1, 1, 1])
print(tokenizer.decode([coord1]))

print("\n2. Testing bhū -> bhaviṣyati (Future, Seṭ)")
# 0 (none), bhu (4), 2 (verb), 3 (future), 1 (third), 1 (singular)
coord2 = TensorCoordinate([0, ROOT_VOCAB.get("bhū", 4), 2, 3, 1, 1])
print(tokenizer.decode([coord2]))

print("\n3. Testing Upasarga: pra + gam -> pragamati")
coord3 = TensorCoordinate([UPASARGA_VOCAB["pra"], ROOT_VOCAB.get("gam", 1), 2, 1, 1, 1])
print(tokenizer.decode([coord3]))

print("\n4. Testing External Sandhi: rāmaḥ gamati")
c_noun = TensorCoordinate([0, ROOT_VOCAB.get("rāma", 5), 1, 1, 1, 1]) # rāma, noun, masc, nom, sing (6D now if we use 6D for noun?)
# Wait, nouns are 5D: [root, pos, gender, case, number]
c_noun = TensorCoordinate([ROOT_VOCAB.get("rāma", 5), 1, 1, 1, 1])
print(tokenizer.decode([c_noun, coord1]))
