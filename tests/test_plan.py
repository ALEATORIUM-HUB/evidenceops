from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from evidenceops.manifest import Manifest, ManifestEntry
from evidenceops.plan import ExecutionPlan, OperationType, build_plan


def test_build_plan():
    manifest = Manifest((ManifestEntry("sample", 3),))
    plan = build_plan(manifest)
    assert plan.operations[0].entry == manifest.entries[0]
    assert plan.operations[0].operation_type is OperationType.VERIFY
    assert datetime.fromisoformat(plan.created_at).utcoffset().total_seconds() == 0
    with pytest.raises(FrozenInstanceError):
        plan.created_at = "changed"


def test_empty_and_defensive_sequence():
    assert build_plan(Manifest(())).operations == ()
    operations = []
    plan = ExecutionPlan(operations, "2026-01-01T00:00:00+00:00")
    operations.append(None)
    assert plan.operations == ()
