# EvidenceOps

Automation needs clear evidence of what it observed and planned.
File inventories and ad hoc logs can be difficult to compare after failures.
EvidenceOps provides small, dependency-free Python building blocks for local
file snapshots, integrity checks, simulated plans, and structured event records.

**v0.1.0 is read-only for audited files: no mutations are performed on inputs.**
The explicitly selected ledger output is written by the append-only API.
Examples create and remove their own temporary synthetic fixtures.

```text
SCAN → MANIFEST → HASH → PLAN → VALIDATE → DRY-RUN → LEDGER
```

## Install from a local checkout

Python 3.11, 3.12, or 3.13 on Linux or macOS is required. Safe filesystem access
uses POSIX descriptor-relative operations. Windows is not supported in v0.1.0.
This package has not been published to PyPI. From this repository directory:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

For library use without development tools, use `python -m pip install -e .`.
There are zero runtime dependencies.

## Five-minute quickstart

These self-contained examples need no external services or private data:

```sh
python examples/01_local_audit.py
python examples/02_dry_run.py
```

Or use the library with an existing local directory:

```python
from pathlib import Path

from evidenceops.gates import DryRunGate, ValidationGate
from evidenceops.hashing import enrich_manifest, verify_manifest
from evidenceops.ledger import AppendOnlyLedger, new_run_id
from evidenceops.manifest import scan
from evidenceops.plan import build_plan

root = Path("sample-data")  # supply your existing audit directory
manifest = enrich_manifest(scan(root), root)
results = verify_manifest(manifest, root)
plan = build_plan(manifest)
validation = ValidationGate()
validation.validate(plan)
simulation = DryRunGate().run(plan, validation)
ledger = AppendOnlyLedger("audit.jsonl", new_run_id())  # outside sample-data
ledger.record("verification", {"results": results})
assert simulation.mutations_executed == 0
```

`ValidationGate` checks plan structure, not live integrity. Call
`verify_manifest` separately to check content; `DryRunGate` only describes
would-be operations and never executes even a VERIFY operation.

## Behavior and limits

- Manifests contain sorted relative POSIX paths, size, kind, and optional SHA-256.
- SHA-256 streams in 64 KiB chunks and enrichment returns a new snapshot.
- Symlinks are represented but never traversed or hashed. For a symlink, `OK`
  means only that kind and size match; link targets are not integrity-verified.
- Verification reports `OK`, `MISSING`, `SIZE_MISMATCH`, or `HASH_MISMATCH`.
  Missing hashes, unsafe paths, unsupported files, and read errors raise exceptions.
  A type change is reported as `HASH_MISMATCH`.
- Verification checks listed entries only; it does not detect newly added files.
  Scan again to compare complete inventories.
- No ignore rules apply automatically: hidden files are included. Select a narrow
  audit root. Directory roots and ancestors must not be symlinks.
- Filesystem observations are not atomic snapshots. Detected changes during hashing
  fail closed, but verification is not a guarantee against hostile concurrent writers.
- The ledger provides an **append-only API** with UTC timestamps and UUID4 `run_id`.
  Filesystem owners can edit the output. Use one writer and a dedicated regular file
  outside the audited tree. No repair, rotation, or concurrent-writer coordination exists.
- No file mutation operations, CLI, cloud adapters, databases, recovery orchestration,
  or AI service integrations are included.

## Development and release checks

```sh
ruff check .
pytest --cov=evidenceops --cov-report=term-missing --cov-fail-under=80
```

CI is configured for Ubuntu and Python 3.11/3.12/3.13. A configured workflow is not
proof of a successful hosted run. See [contribution and release gates](CONTRIBUTING.md)
before tagging or publishing; public pushes require explicit owner authorization.

[Architecture](docs/architecture.md) · [Security](SECURITY.md) ·
[Changelog](CHANGELOG.md) · [Code of conduct](CODE_OF_CONDUCT.md)

Licensed under [Apache-2.0](LICENSE).
