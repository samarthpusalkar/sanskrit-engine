# Sanskrit Engine

Deterministic Sanskrit generation engine prototype.

Goal: encode Paninian rules as data, apply them over a token tape, resolve conflicts deterministically, and generate traceable Sanskrit forms for synthetic dataset generation.

## What Exists

- `Token`: surface text plus tags/features/anubandha metadata.
- `Rule`: data-driven condition + operation model.
- `PratyaharaResolver`: Shiva Sutra/pratyahara lookup.
- `Engine`: match rules, resolve conflicts, mutate state until stable.
- `SanskritParser`: v0 parser with phoneme tokens, word nodes, sandhi split candidates.
- `SanskritGenerator`: v0 sentence generator with explicit morphology templates.
- `RuleBasedMorphology`: derives forms from stem + affix tokens using executable rule packs.
- `RuleEnforcer`: applies executable rules and returns trace/issue evidence.
- `DataLoader`: load normalized JSON rule configs.
- Source-data bridge for `ashtadhyayi-data/pratyahara/data.txt`.
- Sutra importer for `ashtadhyayi-data/sutraani/data.txt`.
- JSONL synthetic dataset generator for LLM/SLM training experiments.
- Sample sandhi/pratyahara rules in `data/sample_rules.json`.
- Tests showing deterministic rule application and conflict resolution.

## Run

```bash
python -m pytest
python examples/run_sample.py
```

## Use Your Data Repo

```python
from sanskrit_engine import PratyaharaResolver

resolver = PratyaharaResolver.from_ashtadhyayi_data(
    "/path/to/ashtadhyayi-data/pratyahara/data.txt"
)
assert resolver.contains("अच्", "अ")
```

```python
from sanskrit_engine import export_rule_stubs, load_sutras

sutras = load_sutras("/path/to/ashtadhyayi-data/sutraani/data.txt")
stubs = export_rule_stubs(sutras)
```

CLI:

```bash
python -m sanskrit_engine.cli export-stubs \
  /path/to/ashtadhyayi-data/sutraani/data.txt \
  data/rule_stubs.json
```

Generate synthetic training records:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl --count 1000 --seed 42
```

With rule enforcement traces:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl \
  --count 1000 \
  --rules data/sample_rules.json
```

With bundled sandhi:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl \
  --count 1000 \
  --sandhi
```

With rule-based morphology plus sandhi:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl \
  --count 1000 \
  --morphology-rules data/rules/subanta.json,data/rules/tinanta.json \
  --sandhi
```

Parse text:

```bash
python -m sanskrit_engine.cli parse "rāmaḥ gacchati"
```

Check encoded-vs-stub rule coverage:

```bash
python -m sanskrit_engine.cli inspect-rules data/rules/sandhi.json
```

Validate derivations:

```bash
python -m sanskrit_engine.cli validate data/fixtures/derivations.json
```

Compare exported source stubs to executable packs:

```bash
python -m sanskrit_engine.cli coverage data/rule_stubs.json \
  data/rules/sandhi.json data/rules/subanta.json data/rules/tinanta.json
```

Hydrate inherited rule configs:

```bash
python -m sanskrit_engine.cli hydrate-rules data/rules/raw.json data/rules/hydrated.json
```

## Current Architecture

1. Source sutras load from `ashtadhyayi-data`.
2. `export-stubs` creates fillable executable rule configs.
3. Humans/LLMs annotate each rule with machine conditions and operations.
4. `hydrate-rules` flattens inherited/anuvritti-like contexts.
5. `Engine` applies rules over token tapes with deterministic conflict resolution.
6. `SanskritParser` parses generated or external text into inspectable structure.
7. `RuleBasedMorphology` derives noun/verb forms from executable rule packs.
8. `SanskritGenerator` creates controlled sentences.
9. `generate-jsonl` writes LLM/SLM training records with forms, glosses, rule IDs, and enforcement traces.

## Hard Truth

This is not all 3983 rules encoded yet. It is the framework that makes encoding possible without hardcoding chaos. Starter packs now cover seed sandhi, a-stem subanta, and present parasmaipada tinanta, with validation fixtures. Next milestone is expanding these packs chapter-by-chapter against traditional examples.

See [ROADMAP.md](/Users/samarthpusalkar/Documents/sanskrit_engine/ROADMAP.md) and [docs/rule_authoring.md](/Users/samarthpusalkar/Documents/sanskrit_engine/docs/rule_authoring.md).

## Rule JSON Shape

```json
{
  "id": "6.1.sample",
  "name": "aka savarne dirghah sample",
  "type": "vidhi",
  "priority": 10,
  "conditions": {
    "target": {"text_in": ["a", "ā"]},
    "right": {"text_in": ["a", "ā"]}
  },
  "operation": {
    "type": "merge_with_right",
    "text": "ā",
    "remove_right": true
  }
}
```

Runtime assumes anuvritti has already been flattened into each rule. Later step: add importer for `samarthpusalkar/ashtadhyayi-data` once final source schema is locked.
