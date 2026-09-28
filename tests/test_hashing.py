import hashlib

import pytest

from evidenceops.hashing import enrich_manifest, sha256_file, verify_manifest
from evidenceops.manifest import scan


def test_hash_and_enrichment(tmp_path):
    path = tmp_path / "sample"
    path.write_bytes(b"abc" * 50000)
    original = scan(tmp_path)
    enriched = enrich_manifest(original, tmp_path)
    expected = hashlib.sha256(b"abc" * 50000).hexdigest()
    assert sha256_file(path) == sha256_file(path) == expected
    assert original.entries[0].sha256 is None
    assert enriched.entries[0].sha256 == expected
    assert verify_manifest(enriched, tmp_path) == {"sample": "OK"}
    path.write_bytes(b"xyz" * 50000)
    assert sha256_file(path) != expected
    assert verify_manifest(enriched, tmp_path) == {"sample": "HASH_MISMATCH"}
    path.write_bytes(b"short")
    assert verify_manifest(enriched, tmp_path) == {"sample": "SIZE_MISMATCH"}
    path.unlink()
    assert verify_manifest(enriched, tmp_path) == {"sample": "MISSING"}


def test_links_and_unhashed_entries(tmp_path):
    (tmp_path / "link").symlink_to("absent")
    manifest = enrich_manifest(scan(tmp_path), tmp_path)
    assert manifest.entries[0].sha256 is None
    assert verify_manifest(manifest, tmp_path) == {"link": "OK"}
    with pytest.raises(OSError):
        sha256_file(tmp_path / "link")
    (tmp_path / "sample").write_bytes(b"a")
    with pytest.raises(ValueError):
        verify_manifest(scan(tmp_path), tmp_path)


def test_size_change_and_symlink_substitution(tmp_path):
    path = tmp_path / "sample"
    path.write_bytes(b"abc")
    original = scan(tmp_path)
    manifest = enrich_manifest(original, tmp_path)
    path.write_bytes(b"abcd")
    with pytest.raises(RuntimeError):
        enrich_manifest(original, tmp_path)
    path.unlink()
    path.symlink_to("missing")
    assert verify_manifest(manifest, tmp_path) == {"sample": "HASH_MISMATCH"}
    with pytest.raises(OSError):
        enrich_manifest(original, tmp_path)


def test_nested_file(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "sample").write_bytes(b"")
    manifest = enrich_manifest(scan(tmp_path), tmp_path)
    assert verify_manifest(manifest, tmp_path) == {"nested/sample": "OK"}


def test_parent_symlink_replacement_blocked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    nested = root / "nested"
    nested.mkdir()
    (nested / "sample").write_bytes(b"abc")
    manifest = enrich_manifest(scan(root), root)
    nested.rename(root / "original")
    nested.symlink_to("original", target_is_directory=True)
    with pytest.raises(OSError):
        verify_manifest(manifest, root)


def test_nonregular_hash_rejected(tmp_path):
    import os

    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(ValueError):
        sha256_file(tmp_path / "pipe")


def test_change_during_hashing_fails_closed(tmp_path, monkeypatch):
    import evidenceops.hashing as hashing

    path = tmp_path / "sample"
    path.write_bytes(b"abc")
    original_fstat = hashing.os.fstat
    calls = 0

    def changing_fstat(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_bytes(b"changed during read")
        return original_fstat(fd)

    monkeypatch.setattr(hashing.os, "fstat", changing_fstat)
    with pytest.raises(RuntimeError, match="changed during hashing"):
        sha256_file(path)


def test_missing_nested_directory(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "sample").write_bytes(b"abc")
    manifest = enrich_manifest(scan(tmp_path), tmp_path)
    (tmp_path / "nested" / "sample").unlink()
    (tmp_path / "nested").rmdir()
    assert verify_manifest(manifest, tmp_path) == {"nested/sample": "MISSING"}
