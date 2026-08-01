# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
