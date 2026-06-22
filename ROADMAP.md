# Sanskrit Engine Roadmap

Goal: deterministic Sanskrit parser + generator + rule-enforcement engine that can generate traceable synthetic data for LLM/SLM training.

## Stage 0: Repo + Core Runtime

Status: complete.

- Data-driven `Rule` schema.
- Mutable token tape.
- Deterministic engine loop.
- Conflict resolver.
- Cycle/max-step guards.
- Trace output.

Evidence: `python -m pytest -q`.

## Stage 1: Source Data Bridge

Status: complete.

- Load `ashtadhyayi-data/sutraani/data.txt`.
- Load `ashtadhyayi-data/pratyahara/data.txt`.
- Export 3983 sutras as executable rule stubs.

Command:

```bash
python -m sanskrit_engine.cli export-stubs \
  /path/to/ashtadhyayi-data/sutraani/data.txt \
  data/rule_stubs.json
```

## Stage 2: Parser v0

Status: complete.

- IAST phoneme tokenizer.
- Word-level parse nodes.
- Basic feature guessing.
- Reversible sandhi split candidates.

Current limit: not full derivational parse. Sandhi splitter has seed rules only.

## Stage 3: Generator v0

Status: complete.

- Tiny lexicon.
- Template noun declension.
- Template present-tense verb conjugation.
- Rule-based morphology mode using executable rule packs.
- Sentence generator with forms, features, glosses, rule IDs.

Current limit: starter rule packs cover only seed subanta/tinanta behavior. Expand encoded derivations rule-by-rule.

## Stage 4: Rule Enforcement

Status: complete.

- `RuleEnforcer` applies executable JSON rules.
- Returns stable/non-stable status, trace, issues.
- JSONL records can include enforcement evidence.

Current limit: only encoded rules execute. Source sutra text alone is not executable.

## Stage 5: Synthetic Dataset Pipeline

Status: complete.

- JSONL writer.
- CLI generation.
- Optional rule enforcement traces.
- Optional bundled sandhi with `--sandhi`.

Command:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl --count 1000 --seed 42
```

## Stage 6: Encode Real Rule Packs

Status: in progress.

Order:

1. Sandhi rules: high impact, easy verification pairs. Started in `data/rules/sandhi.json`.
2. Subanta noun morphology: `a`-stem masculine/neuter/feminine. Started in `data/rules/subanta.json`.
3. Tinanta verb morphology: present parasmaipada. Started in `data/rules/tinanta.json`.
4. Samasa: conservative compounds with explicit semantic labels.
5. Full anuvritti hydration.
6. Conflict resolver expansion: utsarga/apavada, asiddha zones, tripadi behavior.

Deliverable status:

- `data/rules/sandhi.json`: started.
- `data/rules/subanta.json`: started.
- `data/rules/tinanta.json`: started.

Current evidence:

```bash
python -m sanskrit_engine.cli inspect-rules data/rules/sandhi.json
```

shows first executable sandhi pack. Full 3983-sutra coverage remains pending.

Example full v0 pipeline:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl \
  --count 1000 \
  --morphology-rules data/rules/subanta.json,data/rules/tinanta.json \
  --sandhi
```

## Stage 7: Full Mathematical Engine

Status: pending.

- Convert all applicable sutras into executable rule objects.
- Keep non-operational sutras as metadata/paribhasha constraints.
- Build validation suite from traditional examples.
- Add benchmark suite for recursive derivation.
- Generate high-volume JSONL with provenance.
