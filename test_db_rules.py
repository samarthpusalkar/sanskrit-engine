from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *
from sanskrit_engine.rule_database import RuleDatabase

populate_vocabularies("data/dhatu_data.json")
rule_db = RuleDatabase("data/ashtadhyayi_db.json")

token = {"pos": "verb", "text": "ramate"}
env = {
    "root": "ram",
    "pos": "verb",
    "tense": "present",
    "person": "third",
    "number": "singular",
    "voice": "A",
    "gana": "1",
    "settva": "S"
}

applicable = rule_db.get_applicable_rules(token, env)
print(f"Applicable rules: {[r.rule_id for r in applicable]}")

for rule in applicable:
    print(f"Applying rule {rule.rule_id}...")
    token = rule.apply(token, env)
    print(f"Token after: {token}")

