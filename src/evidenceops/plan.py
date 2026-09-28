"""Read-only operation descriptions, with no execution callbacks."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from .manifest import Manifest, ManifestEntry


class OperationType(Enum):
    VERIFY = "verify"
    REPORT = "report"
    NOOP = "noop"


@dataclass(frozen=True)
class Operation:
    entry: ManifestEntry
    operation_type: OperationType
    reason: str = ""


@dataclass(frozen=True)
class ExecutionPlan:
    operations: tuple[Operation, ...]
    created_at: str

    def __post_init__(self):
        object.__setattr__(self, "operations", tuple(self.operations))


def build_plan(manifest: Manifest) -> ExecutionPlan:
    """Describe verification for each entry, including link metadata checks."""
    return ExecutionPlan(
        tuple(Operation(entry, OperationType.VERIFY) for entry in manifest.entries),
        datetime.now(UTC).isoformat(),
    )
