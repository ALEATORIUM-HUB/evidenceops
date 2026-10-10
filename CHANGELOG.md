# Changelog

## 0.1.0 — 2026-10-10

- Deterministic frozen manifests with relative paths and symlink metadata.
- Streaming SHA-256 enrichment and listed-entry verification.
- VERIFY, REPORT, and NOOP plan descriptions.
- Explicit fail-closed structural validation and dry-run simulation.
- JSONL append-only API with UTC timestamps and UUID4 run identifiers.
- Synthetic examples, behavior tests, and enforced 80% minimum coverage.
- CI configuration for Python 3.11, 3.12, and 3.13 on Ubuntu.

Audited inputs remain read-only. The caller-selected evidence ledger is the only
library output write. This release is hosted on GitHub and is not published to a
package registry.
