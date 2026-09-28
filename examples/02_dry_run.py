"""Simulate a plan and show that audited content remains unchanged."""

from pathlib import Path
from tempfile import TemporaryDirectory

from evidenceops.gates import DryRunGate, ValidationGate
from evidenceops.hashing import enrich_manifest
from evidenceops.ledger import AppendOnlyLedger, new_run_id
from evidenceops.manifest import scan
from evidenceops.plan import build_plan

with TemporaryDirectory() as temporary:
    workspace = Path(temporary).resolve()
    root = workspace / "input"
    root.mkdir()
    (root / "sample.txt").write_text("synthetic example\n", encoding="utf-8")
    before = enrich_manifest(scan(root), root)
    plan = build_plan(before)
    validation = ValidationGate()
    validation.validate(plan)
    result = DryRunGate().run(plan, validation)
    assert result.simulated is True and result.mutations_executed == 0
    assert enrich_manifest(scan(root), root) == before
    ledger = AppendOnlyLedger(workspace / "simulation.jsonl", new_run_id())
    ledger.record("dry_run", {"simulated": result.simulated, "mutations_executed": 0})
    print(result)
