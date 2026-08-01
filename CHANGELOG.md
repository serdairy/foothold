# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- `docs` now reports an unwritable `--out` path as a one-line error instead of a
  traceback. Found by the Windows CI matrix, which is why the matrix exists.

### Changed

- `uv.lock` is committed, so CI resolves the same dependency set every run.
- Tagging builds a distribution artifact; publishing to PyPI is gated behind the
  `PYPI_PUBLISH` repository variable until trusted publishing is configured.
- `ARCHITECTURE.md` is refreshed at release time. An earlier attempt to assert it
  byte-for-byte in CI was removed: churn is an input to the ranking, so the document
  legitimately changes with every commit and the check failed by construction.

## [0.1.0]

### Added

- `foothold map` — offline ranking of the files that hold a Python repository together,
  combining PageRank over the in-project import graph, git churn, fan-in and size.
- `foothold docs` — deterministic `ARCHITECTURE.md` with a Mermaid dependency graph.
- `foothold issues` — good-first-issue candidates from TODO markers, untested modules
  and undocumented public APIs, restricted to modules off the critical path.
- `foothold explain` — model-written prose over the ranked map, with `--dry-run` to
  inspect the exact payload and a confirmation prompt before any spend.
- `.foothold.toml` for ranking weights, excludes and model selection.

### Notes

- Python only. Multi-language support via tree-sitter is v0.3.
- PageRank is implemented in pure Python to avoid a scipy/numpy dependency: three small
  runtime dependencies total.
