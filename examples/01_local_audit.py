"""Run a synthetic local audit; all generated data is temporary."""

from pathlib import Path
from tempfile import TemporaryDirectory

from evidenceops.hashing import enrich_manifest, verify_manifest
from evidenceops.ledger import AppendOnlyLedger, new_run_id
from evidenceops.manifest import scan
from evidenceops.plan import build_plan

with TemporaryDirectory() as temporary:
    workspace = Path(temporary).resolve()
    root = workspace / "input"
    root.mkdir()
    (root / "sample.txt").write_text("synthetic example\n", encoding="utf-8")
    manifest = enrich_manifest(scan(root), root)
    plan = build_plan(manifest)
    results = verify_manifest(manifest, root)
    ledger = AppendOnlyLedger(workspace / "audit.jsonl", new_run_id())
    ledger.record("audit", {"results": results, "planned": len(plan.operations)})
    assert results == {"sample.txt": "OK"}
    print(f"Verified {len(results)} file; recorded {len(ledger.read_all())} event.")
