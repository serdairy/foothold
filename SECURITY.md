# Security policy

## Threat model

Foothold reads repositories that its user did not write. That makes untrusted input the
normal case, not the exception. Two properties are load-bearing:

1. **Foothold never executes the code it analyses.** Parsing goes through the stdlib
   `ast` module, which does not evaluate the source. There is no `import`, no `exec`, no
   plugin discovery that runs repository code.
2. **Source code does not leave the machine unless you ask.** `map`, `docs`, `issues` and
   `explain --dry-run` are fully offline. Only `explain` and `docs --narrate` make a
   network call, both require explicit confirmation or `--yes`, and both send the pruned
   context — file paths, scores, docstring first lines — not file contents. Verify with
   `foothold explain . --dry-run`, which prints exactly what would be transmitted.

The `git log` subprocess is invoked with an explicit argv list and no shell.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository, or email
pserg@me.com. Please do not open a public issue.

Expect an acknowledgement within 72 hours and a fix or a mitigation plan within 14 days
for anything that lets a repository under analysis execute code or exfiltrate content.

## Supported versions

Until v1.0, only the latest release receives security fixes.
