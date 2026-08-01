# Foothold

[![CI](https://github.com/serdairy/foothold/actions/workflows/ci.yml/badge.svg)](https://github.com/serdairy/foothold/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/foothold.svg)](https://pypi.org/project/foothold/)
[![Python](https://img.shields.io/pypi/pyversions/foothold.svg)](https://pypi.org/project/foothold/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Which 20 files should I read first?** Foothold answers that for a Python repository in
under a second, without an API key — the foothold you need before you can start climbing
an unfamiliar codebase.

```console
$ foothold map ~/src/rich
99 modules (99 source, 0 test) · 38,437 lines · 1,884 import statements
Top 6 files by structural weight
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ # ┃ file                      ┃ score ┃ in ┃  loc ┃ why                      ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1 │ console.py                │ 0.695 │ 49 │ 2699 │ imported by 49 modules   │
│ 2 │ cells.py                  │ 0.542 │ 31 │  353 │ imported by 31 modules   │
│ 3 │ _unicode_data/__init__.py │ 0.380 │  1 │   94 │ high transitive reach    │
│ 4 │ text.py                   │ 0.353 │ 31 │ 1364 │ imported by 31 modules   │
│ 5 │ style.py                  │ 0.299 │ 30 │  797 │ imported by 30 modules   │
│ 6 │ segment.py                │ 0.220 │ 21 │  781 │ 781 lines                │
└───┴───────────────────────────┴───────┴────┴──────┴──────────────────────────┘
```

That ordering is not a guess. It falls out of the import graph, weighted by how often each
file has been edited.

## The problem

Contributor onboarding is the most expensive unpaid work in open source, and it is paid
twice — once by the newcomer who spends a weekend deciding which of 400 files matter, and
once by the maintainer answering the same orientation question in every issue thread.

The usual mitigations do not hold. `ARCHITECTURE.md` is written once at project inception
and drifts within two releases. Generated API references list every symbol and rank none
of them. Pasting a repository into a chat window costs ~46,000 tokens for a project the
size of networkx, and produces fluent prose with no grounding in the actual import graph.

Foothold splits the problem in two. **Ranking is deterministic** — a graph, a churn
count, a formula you can read. **Prose is optional** and sits on top of an already-correct,
already-pruned selection. The expensive part is the part that does not need a model.

## Install

```bash
uv tool install foothold      # or: pipx install foothold
```

Three runtime dependencies: `typer`, `rich`, `networkx`. PageRank is implemented in pure
Python specifically to avoid pulling ~100 MB of scipy and numpy into a CLI.

## Commands

| Command | What it does | Network |
|---|---|---|
| `foothold map .` | Rank the files that hold the repo together | none |
| `foothold docs . -o ARCHITECTURE.md` | Write a deterministic architecture document with a Mermaid graph | none |
| `foothold issues . --max 10` | Propose good-first-issue candidates, off the critical path | none |
| `foothold explain . --dry-run` | Print the exact payload a model would receive | none |
| `foothold explain .` | Prose walkthrough grounded in the ranked map | OpenAI API |
| `foothold docs . --narrate` | The same document, with an overview section | OpenAI API |

The two commands that cost money print an estimate and require confirmation; `--yes` is
mandatory for non-interactive use.

## How the ranking works

```
score = 0.45·pagerank + 0.30·churn + 0.15·fan-in + 0.10·log(loc)
```

Each term is min-max normalised across the repository, so scores compare within a repo but
not across repos. The weights live in `.foothold.toml` and are printed in every generated
document — a ranking you cannot interrogate is a ranking you cannot trust.

- **PageRank** over the in-project import graph. Edges point *importer → imported*, so a
  module everything depends on scores high. External and stdlib imports are dropped: they
  add nodes without adding signal. (`test_pagerank_ranks_dependencies_above_dependents`
  guards the direction — reversing it silently inverts the whole tool.)
- **Churn** from `git log --since=18.months`. A file edited in every release is a file a
  newcomer will have to touch. Repositories without git history degrade to a zero churn
  signal rather than failing.
- **Fan-in** as a plain, legible count, so the top of the list is explainable without
  understanding PageRank.
- **Size**, log-scaled, as a weak tiebreaker.

Tests are excluded from the ranking and used instead to detect untested modules.

## What it sends, and what it does not

`foothold explain . --dry-run` prints the complete payload. It contains file paths,
scores, entry points, import cycles and the first line of each module docstring. **It does
not contain source code** — there is a test asserting exactly that.

The consequence is that context size tracks `--top`, not repository size:

| Repository | Modules | Lines of code | Context sent | Budgeted tokens |
|---|---:|---:|---:|---:|
| foothold | 31 | 1,284 | 1,999 chars | 899 |
| rich | 99 | 38,437 | 2,314 chars | 978 |
| networkx | 565 | 183,241 | 2,837 chars | 1,109 |

A 183,000-line codebase is described in under 3 KB. Full numbers and method in
[docs/cost-model.md](docs/cost-model.md).

Foothold also never executes the code it reads — parsing is stdlib `ast`, which does not
evaluate. See [SECURITY.md](SECURITY.md).

## Architecture

```
src/foothold/
├── cli.py              # Typer entry point
├── analyze.py          # orchestration: collect → graph → rank → RepoMap
├── models.py           # the shared vocabulary; imported by 10 modules
├── config.py           # .foothold.toml, ranking weights
├── collectors/         # python_ast · git_history · markers    (offline)
├── graph/              # build (import graph) · rank (pagerank + weights)
├── issues.py           # good-first-issue heuristics           (offline)
├── render/             # terminal · markdown · mermaid         (offline)
└── narrator/           # the only module that talks to a model
```

[ARCHITECTURE.md](ARCHITECTURE.md) is generated by `foothold docs` and regenerated by CI
on every push to `main`. If it drifts from reality, that is a bug in Foothold and the
diff makes it public.

## Limitations

Stated plainly, because the alternative wastes your time:

- **Python only.** Other languages are parsed as nothing. tree-sitter support is v0.3.
- Dynamic imports (`importlib`, plugin registries, `__getattr__` re-exports) are invisible
  to static analysis and will under-rank plugin-heavy architectures.
- Churn needs real git history. CI must use `fetch-depth: 0`; shallow clones silently lose
  that signal.
- Monorepos with several independent packages are ranked as one graph. v0.5.
- Scores are comparable within a repository, never across repositories.

## Roadmap

| Version | Scope | Status |
|---|---|---|
| **v0.1** | `map`, `docs`, `issues`, `explain`; Python; 85% coverage | **shipped** |
| v0.2 | Content-hash cache; incremental re-analysis on diff; `--since` | next |
| v0.3 | tree-sitter parsers: TypeScript, JavaScript, Go | planned |
| v0.4 | `tour` with personas; GitHub Action for CI-regenerated docs | planned |
| v0.5 | Monorepo support; call-graph edges, not just imports | planned |
| v1.0 | Stable JSON schema; benchmark suite against hand-written docs | planned |

Non-goals: replacing hand-written design documents, reviewing code, running as a hosted
service. Foothold is a local tool that produces files you own and commit.

## Contributing

Foothold exists because onboarding is hard, so its own onboarding has to be good:

```bash
git clone https://github.com/serdairy/foothold && cd foothold
uv sync --all-extras
uv run foothold map .        # start here
uv run pytest                # 23 tests, ~0.2s, no network
```

If `map` gives you a confusing reading order on your project, open a **bad ranking** issue
— that is the most useful report this project can receive. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0 — chosen over MIT for the explicit patent grant, which matters for a tool that
parses other people's code. See [LICENSE](LICENSE).
