# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.2]

### Fixed

- An empty `__init__.py` could rank first. On codecarbon, a zero-line
  `carbonserver/__init__.py` came top of 283 files: transitive import weight is
  real, but a file with nothing in it is a routing node, not an answer to "what
  should I read first". Package markers with no statements are now kept in the
  graph and left out of the ranking. One holding only a docstring is still
  ranked — a sentence saying what the package is for is worth reading.
- `ARCHITECTURE.md` recommended the wrong files. "Where to start" listed entry
  points — modules nothing else imports — which on highway-env meant benchmark
  scripts and the Sphinx config, under a heading promising the opposite. That
  section is now the ranking itself; entry points keep their own heading, which
  is what they are actually good for.
- `docs/` is excluded by default. Sphinx's `conf.py` ranked 14th of 66 files on
  highway-env, and documentation build configuration is not source a newcomer
  should be sent to read.
- **Reported import cycles were not cycles.** The nodes were sorted
  alphabetically and then printed with arrows between them, so most arrows
  claimed an import that does not exist. Cycles now keep their direction,
  rotated to start at their smallest member, and the output closes the loop:
  `a → b → a`.
- **The cycle list changed on every run.** `networkx.simple_cycles` yields in
  set-iteration order, and taking the first ten gave a different ten per
  process. On highway-env, regenerating `ARCHITECTURE.md` produced a different
  document each time for no reason. Cycles are now deduplicated, sorted shortest
  first, and the scan is bounded so a dense graph cannot hang the run.

### Changed

- `Module` records how many top-level statements a file has, and the cache format
  is `2` so entries written by 0.2.1 are ignored rather than misread.

## [0.2.1]

Findings from an audit of 0.2.0 against hostile and awkward repositories. Two of
these produced a quietly wrong answer, which is worse than an error.

### Fixed

- **Analysing a subdirectory lost the churn signal entirely.** `git log` and
  `git diff` return paths relative to the repository root, while scores are keyed
  relative to the directory being analysed. On django, `foothold map django/`
  ranked 906 files with churn on none of them — 30% of the ranking weight, gone,
  with no warning. Both commands now pass `--relative`.
- **`--since` reported an empty diff for the same reason** when pointed at a
  subdirectory. It now finds the changed files.
- **A ref beginning with a dash was parsed by git as an option.**
  `--since=--output=/tmp/x` made `git diff` write a file at a path of the caller's
  choosing. Refs are now rejected if they start with `-`, and verified with
  `git rev-parse` before use. There was never a shell involved; argv has always
  been explicit.
- **Symlinks pointing outside the repository were followed.** The contents of an
  unrelated file could reach the map, the cache, `ARCHITECTURE.md` and, with the
  action's `comment` input, a public pull request comment. Files that resolve
  outside the analysed root are now skipped; symlinks within it still work.
- The cache file is written `0600`. It holds docstrings of whatever was analysed,
  and the default umask left it world-readable on a shared machine.

### Changed

- The action no longer expands `${{ }}` inside any `run:` block; every value
  arrives through `env:` and is quoted. GitHub substitutes those expressions into
  the script text before bash sees them, so a value carrying shell metacharacters
  would run as code on the runner.
- Pull request comments are truncated at 60,000 characters with a visible note.
  GitHub rejects anything over 65,536, and the result was no comment at all.

## [0.2.0]

### Added

- A content-addressed parse cache. Everything `ast.parse` yields is a pure function
  of a file's bytes, so it is keyed by their SHA-256 and reused until they change.
  On django this takes a run from 3.5s to 0.40s; on rich, 0.32s to 0.06s. The cache
  lives in `~/.cache/foothold`, never inside the analysed repository. Only
  path-independent facts are stored, so a renamed file cannot carry a stale answer
  with it. `foothold cache` shows it, `foothold cache --clear` empties it,
  `--no-cache` skips it.
- `foothold map --since <ref>`: the reading path for a diff. Changed files ranked by
  the usual weight, then everything that imports them, in reading order. Changed
  test files are listed separately rather than lumped in with deleted ones, because
  ranking excludes tests by design.
- Action inputs `since` (use `auto` for the pull request's base branch) and `cache`,
  which restores and saves the parse cache between runs via `actions/cache`.

### Changed

- `analyze()` takes `use_cache`; `collect_modules()` takes an optional cache.
  Parsing is split into `extract()`, which depends only on the file's bytes, and
  `build_records()`, which applies everything derived from the path.

## [0.1.5]

### Added

- `comment: "true"` posts the reading path as a pull request comment and edits that
  same comment on later pushes, instead of leaving it in a job summary that nobody
  opens. Needs `permissions: pull-requests: write`; on fork pull requests the token is
  read-only, so the action warns and falls back to the summary rather than failing.
- `fetch-history` (default `true`). `actions/checkout` clones at depth 1, which leaves
  `git log` empty, the churn term at zero, and the ranking silently reduced to a plain
  import graph. The action now detects a shallow checkout, deepens it, and warns when
  it cannot.

### Changed

- Temporary files use `RUNNER_TEMP` instead of a hardcoded `/tmp`, so the action
  behaves on Windows runners.
- README leads with a copy-pasteable workflow snippet instead of burying it seventy
  lines down, and links the Marketplace listing.

## [0.1.4]

### Changed

- The action's Marketplace name is now "Foothold reading path". GitHub requires that
  name to be unique across every action, user and organisation, and the organisation
  `github.com/FootHold` already holds "Foothold". Nothing else changes: the package is
  still `foothold` on PyPI and the action is still used as `serdairy/foothold@vX.Y.Z`.

## [0.1.3]

### Added

- A GitHub Action. `uses: serdairy/foothold@v0.1.3` runs the tool against the calling
  repository and writes the ranked reading path to the job summary. Composite action, so
  there is no container to pull; it needs no token and no write permission.

### Changed

- Every GitHub Action dependency moved to its current major: checkout v4 to v7,
  setup-python v5 to v7, setup-uv v3 to v9.0.0, upload-artifact v4 to v7,
  download-artifact v4 to v8. The older majors run on Node 20, which GitHub has
  deprecated, so every run printed a warning - including runs in repositories that
  merely use this action. `setup-uv` stopped publishing moving major tags after v7, so
  it is pinned to an exact version.

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
