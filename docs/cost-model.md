# Cost model

Measured, not estimated. Reproduce any row with:

```bash
foothold map <repo> --top 1              # timing
foothold explain <repo> --dry-run | wc -c   # exact bytes that would be sent
```

## Offline pass (`map`, `docs`, `issues`)

Zero tokens, zero network, zero API key.

| Repository | Modules | Lines | `map` wall time |
|---|---:|---:|---:|
| foothold (this repo) | 31 | 1,284 | 0.14 s |
| rich 13.x | 99 | 38,437 | 0.32 s |
| networkx 3.x | 565 | 183,241 | 1.08 s |

Measured on a 2-core Linux container, Python 3.10, cold cache.

## Model pass (`explain`, `docs --narrate`)

The model receives the ranked file list, entry points, docstring first lines and import
cycles — never file contents. Context size is therefore a function of `--top`, not of
repository size, which is the entire point:

| Repository | Lines of code | Context sent | Budgeted tokens |
|---|---:|---:|---:|
| foothold | 1,284 | 1,999 chars | 899 |
| rich | 38,437 | 2,314 chars | 978 |
| networkx | 183,241 | 2,837 chars | 1,109 |

A 183,000-line repository is described in under 3 KB, and the number barely moves as the
repository grows — the ranking absorbs the growth. At `gpt-4o-mini` list pricing that is a
fraction of a cent per `explain`.

For comparison, pasting networkx into a context window is ~46,000 tokens per question and
gets worse with every release.

## Guardrails

- Every command that spends money prints an estimate and asks for confirmation.
  Non-interactive use requires `--yes`.
- `--dry-run` prints the exact payload. Nothing is sent.
- `estimate_tokens` deliberately over-estimates (4 chars per token plus a fixed margin).
  Erring high is the safe direction when someone else is paying.

## Method

Timings are a single cold run of `foothold map --top 1`, output discarded. Context sizes are byte
counts of the string returned by `narrator.build_context` at the default `--top 25`,
measured directly rather than from rendered terminal output, which wraps at terminal
width. Token figures are what `estimate_tokens` budgets (4 chars per token plus a fixed
margin), not a tokeniser count — they over-estimate by design.
