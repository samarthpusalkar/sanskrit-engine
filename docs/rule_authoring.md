# Rule Authoring Guide

Executable rules are JSON objects consumed by `sanskrit_engine.loader.load_rules`.

## Shape

```json
{
  "id": "6.1.101",
  "name": "akaha savarne dirghah",
  "type": "vidhi",
  "priority": 100,
  "scope": "target",
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

## Condition Fields

- `text`: exact token text.
- `text_in`: one of many token texts.
- `text_suffix`: token text must end with suffix.
- `text_prefix`: token text must start with prefix.
- `text_contains`: token text must contain substring.
- `tag`: token must contain tag.
- `has_tags`: token must contain all tags.
- `feature_equals`: token feature map must match.
- `in_pratyahara`: token text must be inside pratyahara set.
- `absent`: context must be absent.

## Operation Types

- `replace_text`
- `merge_with_right`
- `delete`
- `add_tag`
- `remove_tag`
- `set_feature`
- `noop`
- `replace_suffix`
- `replace_prefix`
- `rewrite_boundary`

`rewrite_boundary` supports word-boundary rules:

```json
{
  "type": "rewrite_boundary",
  "old": "aḥ",
  "new": "o",
  "right_old": "a",
  "right_new": "'",
  "remove_right": false
}
```

## Priority Policy

Current resolver rank:

1. `priority`
2. `scope == right_operand`
3. condition specificity
4. later source order

Use `priority` for known meta-rule ordering until deeper paribhasha engine lands.

## Inheritance / Anuvritti

Rule configs can use `inherits` to copy context from earlier rules:

```json
{
  "id": "child",
  "inherits": "parent",
  "conditions": {"right": {"tag": "sup"}},
  "operation": {"type": "delete"}
}
```

Hydrate before runtime:

```bash
python -m sanskrit_engine.cli hydrate-rules raw.json hydrated.json
```

## Encoding Workflow

1. Export stubs from source sutras.
2. Pick small validated rule pack.
3. Fill `conditions` and `operation`.
4. Add tests with expected derivations.
5. Run generator with `--rules`.
6. Inspect JSONL trace evidence.

## Starter Rule Packs

- `data/rules/sandhi.json`: word-boundary sandhi.
- `data/rules/subanta.json`: starter noun inflection.
- `data/rules/tinanta.json`: starter verb inflection.

Use morphology packs during generation:

```bash
python -m sanskrit_engine.cli generate-jsonl data/synthetic.jsonl \
  --morphology-rules data/rules/subanta.json,data/rules/tinanta.json \
  --sandhi
```

Validate after editing:

```bash
python -m sanskrit_engine.cli validate data/fixtures/derivations.json
```
