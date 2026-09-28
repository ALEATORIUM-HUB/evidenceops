# Architecture

EvidenceOps 0.1.0 implements observation, verification, planning, simulation, and
recording. It has no executor for changes to audited inputs.

## Data flow

1. `scan(root)` records regular files and symlink metadata in lexical path order.
2. `enrich_manifest(manifest, root)` creates a new manifest with SHA-256 for files.
3. `verify_manifest(manifest, root)` compares listed paths with current observations.
4. `build_plan(manifest)` creates VERIFY descriptions and a UTC creation time.
5. `ValidationGate.validate(plan)` accepts only nonempty structurally valid plans.
6. `DryRunGate.run(plan, validation)` returns that exact plan with constant simulation
   status and zero mutations; no operation is executed.
7. `AppendOnlyLedger.record` appends a caller-selected event to a dedicated output.

## Models and boundaries

`ManifestEntry` and `Manifest` are frozen dataclasses. Entry paths must be canonical
relative POSIX paths; parent traversal, drive syntax, and backslashes are rejected.
The manifest copies input sequences, sorts entries, and rejects duplicates. There
is no modification time in manifest identity. Size alone is not content identity.

`ExecutionPlan` copies its operation sequence into a tuple. Supported descriptions
are VERIFY, REPORT, and NOOP. Plan timestamps are intentionally variable; manifest
ordering is deterministic. An empty scan is valid; an empty plan cannot pass the gate.
A successful validation is bound to the same plan object. A failed validation clears
prior approval. These are cooperative Python API checks, not an isolation boundary
against code that modifies private attributes or bypasses frozen dataclasses.

## Filesystem safety

Directory descriptors and O_NOFOLLOW prevent following symlink components during
scan, hashing, verification, or ledger opening. Special files fail closed; nonblocking
opens avoid waiting on a substituted pipe. Regular file hashing compares size,
identity and change metadata around the read and checks the final directory entry.
Those transient change checks do not add modification times to manifest identity.

Errors are surfaced, not silently skipped. A deleted listed path is MISSING.
Concurrent filesystems do not provide transactional snapshots here. Path inventories
may change between operations, and malicious writers are outside this version's
consistency guarantees. Use stable input trees or external filesystem snapshots.
Normal reads may update filesystem access times; the library does not request writes
to audited file contents or metadata.

Symlink hashes remain absent. A matching symlink size does not establish the target
text or content. Hash enrichment skips symlink entries entirely. Verification of
regular entries without hashes raises an error instead of reporting success.

## Ledger

The ledger is an append-only API, not an access-control mechanism. Each JSONL record
contains `timestamp`, `run_id`, `event_type`, and `payload`. Pass one UUID4 run ID to
all ledgers used in a run. Multiple sequential runs can share a ledger file.

Serialization completes before the file is opened for appending. Invalid JSON values
are rejected. Writes use append mode followed by fsync; partial writes are retried.
An interrupted final line without a newline prevents further appends and reads.
I/O errors propagate; a failed append can leave a partial record. There is no automatic
rollback or recovery. Single-writer use is required. Existing complete records are
not authenticated, and read_all is inspection rather than schema certification.

The caller must choose a separate evidence output, outside the audit root. Symlink
and multiply linked output files are rejected, but the API cannot infer ownership
or prove an arbitrary regular file is an appropriate destination.

## Scope

Future recovery, stronger evidence protection, and external adapters are ideas only.
No such capabilities are shipped in 0.1.0.
