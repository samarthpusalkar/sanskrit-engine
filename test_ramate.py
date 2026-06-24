from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *

# Explicitly populate vocabularies with dhatu file
populate_vocabularies("data/dhatu_data.json")

tokenizer = TensorTokenizer(RuleBasedMorphology([]))
base = TensorCoordinate([ROOT_VOCAB.get("ram", 904), POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]])
# Mutate to 3rd Person Singular
print(f"Base decode: {tokenizer.decode([base])}")

# Mutate to 1st Person Plural (0 0 0 2 2)
mutated = base + TensorDelta([0, 0, 0, 2, 2])
print(f"Mutated decode (1st Plural): {tokenizer.decode([mutated])}")
