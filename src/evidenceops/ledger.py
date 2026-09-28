"""JSONL append-only API for explicitly selected evidence output files."""

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from .manifest import _parent


def new_run_id() -> str:
    return str(uuid4())


class AppendOnlyLedger:
    """Single-writer ledger. Files remain editable by filesystem owners.

    Choose a dedicated output path outside the audited tree. No directories are
    created, and interrupted final records are rejected rather than repaired.
    """

    def __init__(self, path: str | Path, run_id: str):
        if not isinstance(run_id, str) or UUID(run_id).version != 4:
            raise ValueError("run_id must be a UUID4 string")
        self.path = Path(path)
        self.run_id = str(UUID(run_id))

    def record(self, event_type: str, payload: dict) -> None:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be nonempty")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary")
        line = (
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "run_id": self.run_id,
                    "event_type": event_type,
                    "payload": payload,
                },
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
        with _parent(self.path.parent, self.path.name) as (parent, name):
            fd = os.open(
                name,
                os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=parent,
            )
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError("Ledger requires a dedicated regular file")
                if info.st_size and os.pread(fd, 1, info.st_size - 1) != b"\n":
                    raise ValueError("Ledger contains an incomplete final record")
                remaining = memoryview(line)
                while remaining:
                    written = os.write(fd, remaining)
                    if written == 0:
                        raise OSError("Ledger write made no progress")
                    remaining = remaining[written:]
                os.fsync(fd)
            finally:
                os.close(fd)

    def read_all(self) -> list[dict]:
        try:
            with _parent(self.path.parent, self.path.name) as (parent, name):
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError:
            return []
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Ledger requires a regular file")
            events = []
            for line in stream:
                if not line.endswith("\n"):
                    raise ValueError("Ledger contains an incomplete final record")
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("Ledger record must be an object")
                events.append(event)
            return events
