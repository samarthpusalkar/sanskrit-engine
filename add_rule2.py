import json

filepath = "data/full_demo_db.json"
with open(filepath, "r") as f:
    db = json.load(f)

# Rule 3: nas -> sya
rule_sya = {
    "rule_id": "P. 7.1.12",
    "name": "Ta-nasi-nasam inatsyah",
    "category": "sandhi",
    "priority": 300,
    "domain": ["noun"],
    "conditions": {},
    "operation": {
        "type": "lambda",
        "executable": "lambda token, env: {'pos': token['pos'], 'text': token['text'][:-3] + 'sya', 'applied_rules': token.get('applied_rules', []) + ['P. 7.1.12']} if token['text'].endswith('aṅas') else token"
    }
}

# Rule 4: a + am -> am
rule_am = {
    "rule_id": "P. 6.1.107",
    "name": "Ami Purvah",
    "category": "sandhi",
    "priority": 300,
    "domain": ["noun"],
    "conditions": {},
    "operation": {
        "type": "lambda",
        "executable": "lambda token, env: {'pos': token['pos'], 'text': token['text'][:-3] + 'am', 'applied_rules': token.get('applied_rules', []) + ['Ami Purvah']} if token['text'].endswith('aam') else token"
    }
}

db["rules"].extend([rule_sya, rule_am])

with open(filepath, "w") as f:
    json.dump(db, f, indent=4)
