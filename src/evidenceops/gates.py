"""Structural validation and simulation; no mutation authorization."""

from dataclasses import dataclass, field
from datetime import datetime

from .manifest import ManifestEntry
from .plan import ExecutionPlan, Operation, OperationType


class ValidationError(ValueError):
    """The plan is invalid or has not been explicitly validated."""


class ValidationGate:
    def __init__(self):
        self._validated_plan = None

    def validate(self, plan: ExecutionPlan) -> None:
        """Validate and remember this exact frozen plan; any failure resets state."""
        self._validated_plan = None
        if not isinstance(plan, ExecutionPlan) or not plan.operations:
            raise ValidationError("A nonempty execution plan is required")
        try:
            created = datetime.fromisoformat(plan.created_at)
            if created.tzinfo is None or created.utcoffset() is None:
                raise ValueError("Timestamp must include a timezone")
            paths = set()
            for operation in plan.operations:
                if not isinstance(operation, Operation):
                    raise ValueError("Invalid operation")
                if not isinstance(operation.operation_type, OperationType):
                    raise ValueError("Only read-only operation types are supported")
                if not isinstance(operation.entry, ManifestEntry):
                    raise ValueError("Invalid manifest entry")
                if not isinstance(operation.reason, str):
                    raise ValueError("Reason must be text")
                if operation.entry.path in paths:
                    raise ValueError("Duplicate operation path")
                paths.add(operation.entry.path)
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        self._validated_plan = plan

    def check(self, plan: ExecutionPlan) -> bool:
        """Check prior explicit validation, without authorizing real operations."""
        return self._validated_plan is not None and self._validated_plan is plan


@dataclass(frozen=True)
class DryRunResult:
    plan: ExecutionPlan
    simulated: bool = field(default=True, init=False)
    mutations_executed: int = field(default=0, init=False)


class DryRunGate:
    def run(self, plan: ExecutionPlan, validation: ValidationGate | None = None) -> DryRunResult:
        """Return would-be operations only; does not read files or execute VERIFY."""
        if not isinstance(validation, ValidationGate) or not validation.check(plan):
            raise ValidationError("Explicit validation of this exact plan is required")
        return DryRunResult(plan)
