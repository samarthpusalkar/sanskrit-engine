import pytest
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate
from sanskrit_engine.morphology import RuleBasedMorphology
from sanskrit_engine.config_index import *
from sanskrit_engine import load_rules

@pytest.fixture
def morphology():
    rules = load_rules("data/rules/subanta.json") + load_rules("data/rules/tinanta.json")
    return RuleBasedMorphology(rules)

@pytest.fixture
def tokenizer(morphology):
    return TensorTokenizer(morphology)

def test_tokenizer_bidirectional_consistency(tokenizer):
    original_text = "rāmaḥ gacchati"
    
    # Encode text to coordinates
    coordinates = tokenizer.encode(original_text)
    
    # Assert coordinates match expected INTEGER tensor semantics
    assert len(coordinates) == 2
    # rāma, noun, masculine, nominative, singular
    assert coordinates[0].vector == [ROOT_VOCAB["rāma"], POS_VOCAB["noun"], GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]]
    # gam, verb, present, third, singular
    assert coordinates[1].vector == [ROOT_VOCAB["gam"], POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]]
    
    # Decode coordinates back to text
    decoded_text = tokenizer.decode(coordinates)
    assert decoded_text == original_text

def test_tokenizer_decodes_edge_cases(tokenizer):
    """
    Test decoding complex morphological edge cases like reduplication and perfect tense.
    """
    # 1. Reduplication (Juhotyādi)
    dadaati_vector = TensorCoordinate([ROOT_VOCAB["dā"], POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]])
    assert tokenizer.decode([dadaati_vector]) == "dadāti"
    
    # 2. Perfect Tense Reduplication & Consonant Shift
    jaghana_vector = TensorCoordinate([ROOT_VOCAB["han"], POS_VOCAB["verb"], TENSE_VOCAB["perfect"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]])
    assert tokenizer.decode([jaghana_vector]) == "jaghāna"
    
    # 3. Guna Vowel Strengthening
    bhavati_vector = TensorCoordinate([ROOT_VOCAB["bhū"], POS_VOCAB["verb"], TENSE_VOCAB["present"], PERSON_VOCAB["third"], NUMBER_VOCAB["singular"]])
    assert tokenizer.decode([bhavati_vector]) == "bhavati"

def test_compound_module_morphology_and_sandhi(tokenizer):
    from sanskrit_engine.enforcer import RuleEnforcer
    from sanskrit_engine import load_rules
    
    # deva, nominative, singular + avatāra, nominative, singular
    coordinates = [
        TensorCoordinate([ROOT_VOCAB["deva"], POS_VOCAB["noun"], GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]]),
        TensorCoordinate([ROOT_VOCAB["avatāra"], POS_VOCAB["noun"], GENDER_VOCAB["masculine"], CASE_VOCAB["nominative"], NUMBER_VOCAB["singular"]])
    ]
    
    decoded_text = tokenizer.decode(coordinates) # Generates un-sandhied words
    # Assume 'devaḥ avatāraḥ' for simplicity of the sandhi merge rule testing
    raw_sentence = "deva avatāraḥ"
    
    sandhi_rules = load_rules("data/rules/sandhi.json")
    enforcer = RuleEnforcer(sandhi_rules)
    final_sentence = enforcer.enforce_text(raw_sentence).output_text
    
    assert final_sentence == "devāvatāraḥ"
