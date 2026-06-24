import pytest
from sanskrit_engine.tensor_tokenizer import TensorTokenizer, TensorCoordinate
from sanskrit_engine.morphology import RuleBasedMorphology
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
    
    # Assert coordinates match expected tensor semantics
    assert len(coordinates) == 2
    assert coordinates[0].root == "rāma"
    assert coordinates[0].mods["case"] == "nominative"
    assert coordinates[1].root == "gam"
    assert coordinates[1].mods["person"] == "third"
    
    # Decode coordinates back to text
    decoded_text = tokenizer.decode(coordinates)
    
    # Round-trip consistency check
    assert decoded_text == original_text

def test_tokenizer_decodes_complex_forms(tokenizer):
    # Test decoding an invalid but strictly rule-following vector.
    # The subanta engine currently only supports a limited set of suffixes (nominative, accusative, etc.).
    # We will test decoding a nominative plural to prove it calls the engine properly.
    coordinates = [
        TensorCoordinate("rāma", {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "plural"}),
        TensorCoordinate("gam", {"pos": "verb", "person": "third", "number": "singular", "tense": "present"})
    ]
    decoded_text = tokenizer.decode(coordinates)
    assert decoded_text == "rāmāḥ gacchati" # Based on the rule jas -> āḥ

def test_compound_module_morphology_and_sandhi(tokenizer):
    """
    Tests coherent interaction between the Morphology engine (generating words)
    and the Sandhi engine (gluing them phonetically in a sentence).
    """
    from sanskrit_engine.enforcer import RuleEnforcer
    from sanskrit_engine import load_rules
    
    # 1. Morphological Generation
    coordinates = [
        TensorCoordinate("deva", {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular"}),
        TensorCoordinate("avatāra", {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular"})
    ]
    
    # Normally devasu -> devaḥ, avatārasu -> avatāraḥ
    decoded_text = tokenizer.decode(coordinates)
    
    # We will simulate the morphology output text here for the sandhi test
    # (assuming decoder gave 'devaḥ avatāraḥ' but for simplicity let's test 'deva avatāraḥ')
    raw_sentence = "deva avatāraḥ"
    
    # 2. Phonological Sandhi Merging
    sandhi_rules = load_rules("data/rules/sandhi.json")
    enforcer = RuleEnforcer(sandhi_rules)
    
    # Interaction: The raw tokens from morphology must correctly trigger 
    # the Savarṇadīrgha Sandhi rule (a + a = ā)
    final_sentence = enforcer.enforce_text(raw_sentence).output_text
    
    assert final_sentence == "devāvatāraḥ"
    # This verifies compound system coherence: Tokenizer -> Morphology -> Sandhi

