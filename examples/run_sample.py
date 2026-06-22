from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from sanskrit_engine import Engine, Token, load_rules


rules = load_rules(root / "data" / "sample_rules.json")
engine = Engine(rules)

result = engine.process([Token("rāma"), Token("a"), Token("iti", {"it"}), Token("a")])

print(result.text)
print(result.halted_reason)
for step in result.trace:
    print(step.rule_id, step.rule_name)
