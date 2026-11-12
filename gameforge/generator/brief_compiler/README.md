# Brief compiler (stage 0)

This CLI validates a structured GameSpec against the JSON Schema and creates a reproducible workspace containing the normalised specification and explicit pipeline status flags.

It does **not** yet turn arbitrary natural language into a complete game, generate original assets, prove mechanic novelty, or mark a project as playable. Those are later autonomous pipeline stages.

## Run locally

```bash
python -m pip install -r gameforge/generator/brief_compiler/requirements.txt
python gameforge/generator/brief_compiler/compile.py \
  --spec gameforge/examples/sample-game-spec.json \
  --out build/the-quiet-between
```

The output records what has and has not happened so later automation cannot confuse a validated brief with a tested release.
