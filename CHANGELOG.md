# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.3]

### Added

- A GitHub Action. `uses: serdairy/foothold@v0.1.3` runs the tool against the calling
  repository and writes the ranked reading path to the job summary. Composite action, so
  there is no container to pull; it needs no token and no write permission.

### Changed

- Every GitHub Action dependency moved to its current major: checkout v4 to v7,
  setup-python v5 to v7, setup-uv v3 to v9, upload-artifact v4 to v7,
  download-artifact v4 to v8. The older majors run on Node 20, which GitHub has
  deprecated, so every run printed a warning - including runs in repositories that
  merely use this action.

## [0.1.2]

### Fixed

- `foothold --version` printed a stale number. The version lived in a constant in `__init__.py` that drifted from `pyproject.toml` during the 0.1.1 release. It is now read from package metadata, so the two cannot disagree again.

## [0.1.1]

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

Tagged before PyPI trusted publishing was configured, so this version exists as a git tag only. The first version on PyPI is 0.1.1.

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
