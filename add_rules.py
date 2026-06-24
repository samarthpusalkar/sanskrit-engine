import json

filepath = "data/full_demo_db.json"
with open(filepath, "r") as f:
    db = json.load(f)

# Rule 1: gam -> gacch in present tense
rule_gam = {
    "rule_id": "P. 7.3.77",
    "name": "Isu-gami-yamam Chah",
    "category": "vidhi",
    "priority": 200,
    "domain": ["verb"],
    "conditions": {},
    "operation": {
        "type": "lambda",
        "executable": "lambda token, env: {'pos': token['pos'], 'text': token['text'].replace('gam', 'gacch'), 'applied_rules': token.get('applied_rules', []) + ['P. 7.3.77 (Isu-gami-yamam Chah)']} if env.get('root') == 'gam' and env.get('tense') == 'present' else token"
    }
}

# Rule 2: su -> h
rule_visarga = {
    "rule_id": "P. 8.2.66_8.3.15",
    "name": "Sasajuso Ruh & Kharavasanayor Visarjaniyah",
    "category": "sandhi",
    "priority": 300,
    "domain": ["noun"],
    "conditions": {},
    "operation": {
        "type": "lambda",
        "executable": "lambda token, env: {'pos': token['pos'], 'text': token['text'][:-2] + 'ḥ', 'applied_rules': token.get('applied_rules', []) + ['Visarga Sandhi']} if token['text'].endswith('su') else token"
    }
}

db["rules"].extend([rule_gam, rule_visarga])

with open(filepath, "w") as f:
    json.dump(db, f, indent=4)
print("Rules added successfully.")
