import json
from uuid import UUID

import pytest

from evidenceops.ledger import AppendOnlyLedger, new_run_id


def test_append_preserves_history(tmp_path):
    path = tmp_path / "events.jsonl"
    run_id = new_run_id()
    assert UUID(run_id).version == 4
    ledger = AppendOnlyLedger(path, run_id)
    assert ledger.read_all() == []
    ledger.record("scan", {"count": 1, "note": "line\nbreak"})
    first = path.read_bytes()
    ledger.record("report", {"count": 2})
    assert path.read_bytes().startswith(first)
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["run_id"] for line in lines] == [run_id, run_id]
    assert [event["event_type"] for event in ledger.read_all()] == ["scan", "report"]
    assert not hasattr(ledger, "update_event")
    assert not hasattr(ledger, "delete_event")


def test_invalid_events_do_not_write(tmp_path):
    path = tmp_path / "events.jsonl"
    ledger = AppendOnlyLedger(path, new_run_id())
    for event_type, payload in [("", {}), ("scan", []), ("scan", {"x": float("nan")})]:
        with pytest.raises(ValueError):
            ledger.record(event_type, payload)
    assert not path.exists()
    with pytest.raises(ValueError):
        AppendOnlyLedger(path, "bad-id")


def test_incomplete_record_and_links_blocked(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_bytes(b'{"incomplete":')
    ledger = AppendOnlyLedger(path, new_run_id())
    with pytest.raises(ValueError):
        ledger.record("scan", {})
    with pytest.raises(ValueError):
        ledger.read_all()
    assert path.read_bytes() == b'{"incomplete":'
    link = tmp_path / "link"
    link.symlink_to(path.name)
    with pytest.raises(OSError):
        AppendOnlyLedger(link, new_run_id()).record("scan", {})
    with pytest.raises(OSError):
        AppendOnlyLedger(link, new_run_id()).read_all()


def test_hardlink_ledger_rejected(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_bytes(b"")
    (tmp_path / "alias").hardlink_to(path)
    with pytest.raises(ValueError):
        AppendOnlyLedger(path, new_run_id()).record("scan", {})
    assert path.read_bytes() == b""


def test_multiple_runs_remain_distinguishable(tmp_path):
    path = tmp_path / "events.jsonl"
    first, second = new_run_id(), new_run_id()
    AppendOnlyLedger(path, first).record("scan", {})
    other = AppendOnlyLedger(path, second)
    other.record("scan", {})
    assert [event["run_id"] for event in other.read_all()] == [first, second]


def test_invalid_record_and_uuid_version(tmp_path):
    path = tmp_path / "events.jsonl"
    with pytest.raises(ValueError):
        AppendOnlyLedger(path, "00000000-0000-1000-8000-000000000000")
    path.write_text("[]\n")
    with pytest.raises(ValueError):
        AppendOnlyLedger(path, new_run_id()).read_all()


def test_write_failure_propagates(tmp_path, monkeypatch):
    import evidenceops.ledger as module

    monkeypatch.setattr(module.os, "write", lambda *args: 0)
    with pytest.raises(OSError, match="no progress"):
        AppendOnlyLedger(tmp_path / "events.jsonl", new_run_id()).record("scan", {})
