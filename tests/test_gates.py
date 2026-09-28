from dataclasses import FrozenInstanceError, replace

import pytest

from evidenceops.gates import DryRunGate, DryRunResult, ValidationError, ValidationGate
from evidenceops.manifest import Manifest, ManifestEntry, scan
from evidenceops.plan import ExecutionPlan, Operation, OperationType, build_plan


def test_fail_closed_and_validation_bound_to_plan():
    plan = build_plan(Manifest((ManifestEntry("sample", 0),)))
    validation = ValidationGate()
    assert not validation.check(plan)
    with pytest.raises(ValidationError):
        DryRunGate().run(plan)
    with pytest.raises(ValidationError):
        DryRunGate().run(plan, validation)
    validation.validate(plan)
    assert validation.check(plan)
    with pytest.raises(ValidationError):
        DryRunGate().run(replace(plan), validation)
    with pytest.raises(ValidationError):
        validation.validate(build_plan(Manifest(())))
    assert not validation.check(plan)


def test_simulation_does_not_mutate(tmp_path):
    (tmp_path / "sample").write_bytes(b"synthetic data")
    before = scan(tmp_path)
    contents = (tmp_path / "sample").read_bytes()
    plan = build_plan(before)
    validation = ValidationGate()
    validation.validate(plan)
    result = DryRunGate().run(plan, validation)
    assert result.plan.operations == plan.operations
    assert result.simulated is True
    assert result.mutations_executed == 0
    assert scan(tmp_path) == before
    assert (tmp_path / "sample").read_bytes() == contents
    with pytest.raises(FrozenInstanceError):
        result.simulated = False
    with pytest.raises(TypeError):
        DryRunResult(plan, simulated=False)


@pytest.mark.parametrize(
    "operations,created_at",
    [
        ((), "2026-01-01T00:00:00+00:00"),
        ((None,), "2026-01-01T00:00:00+00:00"),
        ((Operation(ManifestEntry("a", 0), "delete"),), "2026-01-01T00:00:00+00:00"),
        ((Operation(None, OperationType.NOOP),), "2026-01-01T00:00:00+00:00"),
        (
            (Operation(ManifestEntry("a", 0), OperationType.NOOP, None),),
            "2026-01-01T00:00:00+00:00",
        ),
        ((Operation(ManifestEntry("a", 0), OperationType.NOOP),), "bad"),
        ((Operation(ManifestEntry("a", 0), OperationType.NOOP),), "2026-01-01"),
    ],
)
def test_invalid_plan(operations, created_at):
    with pytest.raises(ValidationError):
        ValidationGate().validate(ExecutionPlan(operations, created_at))


def test_duplicate_operations():
    operation = Operation(ManifestEntry("a", 0), OperationType.REPORT)
    with pytest.raises(ValidationError):
        ValidationGate().validate(ExecutionPlan((operation, operation), "2026-01-01T00:00:00Z"))


def test_simulation_never_reads_or_executes_files():
    plan = build_plan(Manifest((ManifestEntry("nonexistent", 99),)))
    validation = ValidationGate()
    validation.validate(plan)
    result = DryRunGate().run(plan, validation)
    assert result.plan.operations[0].entry.path == "nonexistent"
    assert result.mutations_executed == 0
