# Contributing to Foothold

This document should get you from a fresh clone to a merged pull request without needing
to ask anyone anything. If it fails at that, the failure is a bug worth an issue.

## Orientation

The fastest path into this codebase is the tool itself:

```bash
git clone https://github.com/serdairy/foothold && cd foothold
uv sync --all-extras
uv run foothold map .          # offline, no API key
uv run foothold issues .       # what needs doing, ranked off the critical path
```

`src/foothold/models.py` is the shared vocabulary and is imported by ten modules — read
it first. Then `analyze.py`, which is 40 lines and shows the whole pipeline. Then whichever
stage you are changing.

## Development setup

Requirements: Python 3.10+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync --all-extras            # runtime + dev + narrate extras
uv run pre-commit install       # ruff + mypy on commit
uv run pytest                   # 23 tests, ~0.2s, no network
uv run mypy                     # strict, and it must stay clean
uv run pytest -m e2e            # requires OPENAI_API_KEY
```

Unit tests must never open a socket. The `no_network` fixture in `tests/conftest.py` is
applied automatically and fails any test that tries; only tests marked `e2e` are exempt.

## Project conventions

- **Type hints are mandatory.** `mypy --strict` runs in CI and blocks merge.
- **Formatting and linting**: `ruff format` and `ruff check`, enforced by pre-commit.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat:`, `fix:`, `docs:`, `perf:`, `refactor:`, `test:`, `chore:`.
- **Branches**: `feat/short-description`, `fix/issue-123`.
- **New collectors** implement the pattern in `collectors/` — a pure function from a path
  to data, no side effects — and ship with a fixture repository under
  `tests/fixtures/` whose correct graph is written by hand. No fixture, no merge.
- **Ranking changes** require before/after `foothold map` output on at least two real
  repositories in the PR description. Ranking quality is the product; a change to
  `graph/rank.py` without evidence is not reviewable.
- **Prompt changes** require the same: before/after generated output on two fixtures.

## Two invariants that must not break

1. **Foothold never executes the code it analyses.** Parsing is stdlib `ast`. Any change
   that imports, `exec`s, or otherwise runs a target repository will be rejected.
2. **Source code never leaves the machine.** `narrator/client.build_context` sends paths,
   scores and docstring first lines only. `test_context_is_bounded_and_excludes_source`
   guards this. If you need more context for a prompt, say so in an issue first.

## Where to start

| Label | What it means |
|---|---|
| `good first issue` | Self-contained, under ~50 lines, no architectural decisions |
| `ranking` | The output was misleading on a real repository — highest-value work here |
| `parser` | Language support: tree-sitter grammars for v0.3 |
| `help wanted` | Well-specified but larger |
| `needs-design` | Discuss in the issue before writing code |

If nothing fits, open an issue describing what you want to build before you build it. A
short discussion up front is cheaper for both of us than a rejected pull request.

## Pull request checklist

1. An issue exists and is referenced (`Closes #123`).
2. `uv run pytest` and `uv run mypy` pass locally.
3. New behaviour has a test. Coverage must stay above 80% — CI enforces it.
4. User-visible changes update `README.md` in the same PR.
5. If token usage changed, `docs/cost-model.md` is updated with fresh measurements.

Pull requests get an automated review pass for style and obvious defects, then a human
review. The automated pass is advisory; a maintainer makes the merge decision.

## Reporting bugs

Open an issue with the output of `foothold map . --json`, your Python version, and the
repository you ran against (a link is enough if it is public).

For output-quality problems — a wrong reading order, a misleading summary — use the **bad
ranking** template and say what ordering you expected instead. Those reports are the most
valuable ones this project receives, because they are the only external check on whether
the ranking formula is right.

## Security

Do not open a public issue for security problems. See [SECURITY.md](SECURITY.md).

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).

## License

By contributing you agree that your contributions are licensed under Apache-2.0. No CLA
is required.
