import signal
import sys
from sanskrit_engine import GenerativePaniniMorphology, TensorTokenizer, load_rules, TensorCoordinate
from sanskrit_engine.config_index import ROOT_VOCAB, POS_VOCAB, PERSON_VOCAB, NUMBER_VOCAB, TENSE_VOCAB

def handler(signum, frame):
    raise Exception("Timeout! " + str(frame.f_code.co_name))

signal.signal(signal.SIGALRM, handler)

print("Loading...")
rules = load_rules("data/rules/panini_ir_grammar.json")
morphology = GenerativePaniniMorphology(rules)
tokenizer = TensorTokenizer(morphology, default_dim=11)

print("Testing decode...")
count = 0
for r_str, r_id in list(ROOT_VOCAB.items())[:10]:
    for p_name, p_id in list(PERSON_VOCAB.items())[:3]:
        for n_name, n_id in list(NUMBER_VOCAB.items())[:3]:
            vec = [r_id, 2, 0, 0, 0, 1, p_id, 1, 0, 0, n_id]
            coord = TensorCoordinate(vec)
            try:
                signal.alarm(1)
                surf = tokenizer.decode([coord])
                signal.alarm(0)
                print(f"Decoded {r_str} -> {surf}")
            except Exception as e:
                print(f"Failed on {r_str}: {e}")
                sys.exit(1)
