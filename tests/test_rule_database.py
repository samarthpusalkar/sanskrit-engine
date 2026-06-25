import pytest
import os
from sanskrit_engine.config_index import ROOT_VOCAB, populate_vocabularies
from sanskrit_engine.rule_database import RuleDatabase, PaniniRule

def test_config_index_dhatu_population():
    # Attempt to load the 2000+ dhatus from the downloaded data/dhatu_data.json
    data_path = "data/dhatu_data.json"
    if os.path.exists(data_path):
        populate_vocabularies(data_path)
        # Should contain the initial 8 plus the unique ones from the JSON (total ~1726)
        assert len(ROOT_VOCAB) > 1700
        # Check if a known random dhatu is inside
        assert "एध" in ROOT_VOCAB or "भू" in ROOT_VOCAB
        populate_vocabularies()  # Restore standard vocabularies after test
    else:
        pytest.skip("dhatu_data.json not found locally to test massive population.")

def test_rule_database_lambda_execution():
    # Clean up old test db if exists
    db_path = "data/test_db.json"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    # Create an in-memory rule database mapping
    db = RuleDatabase(db_path)
    
    # Insert a complex rule using the LLM compiler's JSON schema format
    mock_rule_data = {
        "rule_id": "6.1.101",
        "name": "akaha savarne dirghah",
        "category": "vidhi",
        "priority": 100,
        "domain": ["noun", "verb"],
        "conditions": {
            "target": {"ends_with_vowel": True}
        },
        "operation": {
            "type": "lambda",
            # A lambda to simulate Sandhi: merge "a" and "a" into "ā"
            "executable": "lambda token, env: {'pos': token.get('pos'), 'text': (token['text'][0][:-1] + 'ā', token['text'][1][1:]) if token['text'][0][-1] == 'a' and token['text'][1][0] == 'a' else token['text']}"
        }
    }
    
    # We test the rule explicitly
    rule = PaniniRule(mock_rule_data)
    
    # Mock token environment for the rule
    # e.g., token representing two words coming together: rāma + avatāra
    token = {"pos": "noun", "text": ("rāma", "avatāra")}
    
    # Apply the rule operation
    result = rule.apply(token, {})
    
    assert result["text"] == ("rāmā", "vatāra")
    
    # Verify that the database stores and retrieves it
    db.insert_rule(mock_rule_data)
    
    # Retrieve applicable rules
    applicable = db.get_applicable_rules({"pos": "noun"}, {})
    assert len(applicable) == 1
    assert applicable[0].rule_id == "6.1.101"
