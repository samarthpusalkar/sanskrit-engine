import signal
import sys
from sanskrit_engine import GenerativePaniniMorphology, TensorTokenizer, load_rules, TensorCoordinate
from sanskrit_engine.config_index import ROOT_VOCAB, POS_VOCAB, PERSON_VOCAB, NUMBER_VOCAB, TENSE_VOCAB

print("Loading...")
rules = load_rules("data/rules/panini_ir_grammar.json")
morphology = GenerativePaniniMorphology(rules)

engine = morphology.engine
# patch engine to stop after 100 steps and print trace
original_run = engine.run_sapadasaptadhyayi
def patched_run(state, trace, seen, sapada_rules):
    engine.max_steps = 20
    status = original_run(state, trace, seen, sapada_rules)
    for t in trace:
        print(t.rule_id, t.rule_name, [tok.text for tok in state])
    sys.exit(1)
engine.run_sapadasaptadhyayi = patched_run

tokenizer = TensorTokenizer(morphology, default_dim=11)

print("Testing decode...")
vec = [ROOT_VOCAB["a"], 2, 0, 0, 0, 1, 1, 1, 0, 0, 1]
coord = TensorCoordinate(vec)
tokenizer.decode([coord])
