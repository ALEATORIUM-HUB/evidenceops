# Contributing

Install from the local checkout with `python -m pip install -e '.[dev]'`.
Run `ruff check .`, then `pytest --cov=evidenceops --cov-report=term-missing
--cov-fail-under=80` on Python 3.11, 3.12, and 3.13. Run both examples as well.
Tests exercise observable behavior and failures, not just the coverage percentage.

Use feat, fix, docs, chore, test, or ci commit prefixes. Keep the read-only input
boundary and zero runtime dependencies. Use synthetic fixtures only.

## Pull request description template

- Problem and intended behavior
- Implementation and scope
- Validation performed and results
- Known limits or security considerations

Suggested issue labels: bug, enhancement, documentation, security. Report sensitive
vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Release procedure

1. Confirm tests, lint, examples, editable installation, and package build pass.
2. Confirm hosted CI is green for Python 3.11, 3.12, and 3.13. Local runs do not
   substitute for a hosted CI result in the initial release gate.
3. Review every tracked file and all historical commits for private data and personal
   paths. Run `gitleaks git . --redact` for history and `gitleaks dir . --redact`
   for the working tree. Require zero findings or stop for investigation.
4. Confirm a clean worktree and obtain explicit owner authorization before any
   public push or publication. Do not infer this from successful tests.
5. Only after every gate passes, create the local tag with `git tag v0.1.0`.
   Tag creation does not authorize pushing it or creating a hosted release.
6. Rerun the security gate before each public push, including a tag push.

If hosted CI is unavailable because publication has not been authorized, keep the
release untagged and document that pending gate. Do not publish to a package registry
as part of 0.1.0. The package name's registry availability has not been established.
