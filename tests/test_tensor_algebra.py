import pytest
import os
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate, TensorDelta
from sanskrit_engine.rule_database import RuleDatabase, PaniniRule
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine import load_rules
from sanskrit_engine.config_index import *

@pytest.fixture
def clean_db():
    db_path = "data/test_algebra_db.json"
    if os.path.exists(db_path):
        os.remove(db_path)
    return RuleDatabase(db_path)

@pytest.fixture
def tokenizer(clean_db):
    # Dummy morphology base
    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    morphology = RuleBasedMorphology(rules)
    return TensorTokenizer(morphology, rule_db=clean_db)

def test_custom_matrix_surgery(tokenizer, clean_db):
    """
    Proves that we can perform custom matrix surgery to change a word's semantics
    (e.g., changing tense) and that the tokenizer fetches Paninian rules from the DB
    instead of relying on manual iterations.
    """
    # 1. Base Matrix: root=bhū (4), verb (2), present (1), third (1), singular (1)
    # Theoretically outputs "bhavati"
    base_vector = TensorCoordinate([ROOT_VOCAB.get("bhū", 4), POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]])
    
    # 2. Custom Matrix Surgery: Shift tense (pos 2) by +1 to make it perfect tense (2)
    delta = TensorDelta([0, 0, 1, 0, 0])
    perfect_vector = base_vector + delta
    
    assert perfect_vector.vector == [ROOT_VOCAB.get("bhū", 4), POS_VOCAB["verb"], TENSE_VOCAB["perfect"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]]
    
    # 3. Seed the Database with a Panini Rule that catches "bhū" + "perfect"
    # and transforms it into "babhūva" (without hardcoding it in the Tokenizer!)
    perfect_bhu_rule = {
        "rule_id": "bhu_perfect_redup",
        "name": "Bhu Perfect Reduplication",
        "category": "vidhi",
        "priority": 100,
        "domain": ["verb"],
        "conditions": {
            # RuleDB will check these conditions against the vector's `env`
            "target": {"dummy": True} 
        },
        "operation": {
            "type": "lambda",
            # We apply the transformation only if env matches root=bhū and tense=perfect
            "executable": "lambda token, env: {'pos': token['pos'], 'text': 'babhūva'} if env.get('root') == 'bhū' and env.get('tense') == 'perfect' else token"
        }
    }
    
    # Also seed a rule for 'dadāti' reduplication to prove present tense intercepting works
    dadaati_rule = {
        "rule_id": "juhotyadi_dadaati",
        "name": "Juhotyadi Reduplication",
        "category": "vidhi",
        "priority": 100,
        "domain": ["verb"],
        "operation": {
            "type": "lambda",
            "executable": "lambda token, env: {'pos': token['pos'], 'text': 'dadāti'} if env.get('root') == 'dā' and env.get('tense') == 'present' else token"
        }
    }
    
    clean_db.insert_rule(perfect_bhu_rule)
    clean_db.insert_rule(dadaati_rule)
    
    # 4. DECODE
    # The tokenizer does NOT have manual hardcoded strings for "babhūva".
    # It must fetch it from the db.
    word = tokenizer.decode([perfect_vector])
    assert word == "babhūva"
    
    # Let's test dadāti just to be sure
    dada_vector = TensorCoordinate([ROOT_VOCAB.get("dā", 3), POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]])
    dada_word = tokenizer.decode([dada_vector])
    assert dada_word == "dadāti"
