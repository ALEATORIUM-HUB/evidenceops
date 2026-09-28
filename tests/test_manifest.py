from dataclasses import FrozenInstanceError

import pytest

from evidenceops.manifest import Manifest, ManifestEntry, scan


def test_scan_is_deterministic_relative_and_frozen(tmp_path):
    (tmp_path / "z").write_bytes(b"last")
    (tmp_path / "folder").mkdir()
    (tmp_path / "folder" / "a").write_bytes(b"first")
    actual = scan(tmp_path)
    assert actual == scan(tmp_path)
    assert [e.path for e in actual.entries] == ["folder/a", "z"]
    assert [e.size for e in actual.entries] == [5, 4]
    with pytest.raises(FrozenInstanceError):
        actual.entries = ()


def test_links_are_not_followed(tmp_path):
    (tmp_path / "link").symlink_to("missing")
    (tmp_path / "loop").symlink_to(".", target_is_directory=True)
    assert [e.kind for e in scan(tmp_path).entries] == ["symlink", "symlink"]
    with pytest.raises(ValueError):
        scan(tmp_path, follow_symlinks=True)
    with pytest.raises(OSError):
        scan(tmp_path / "loop")


@pytest.mark.parametrize("path", ["/absolute", "../escape", "a/../b", "a//b", "", "C:/x"])
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError):
        ManifestEntry(path, 0)


def test_invalid_entries(tmp_path):
    for kwargs in (
        {"size": -1},
        {"size": True},
        {"size": 0, "kind": "fifo"},
        {"size": 0, "sha256": "bad"},
    ):
        with pytest.raises(ValueError):
            ManifestEntry("sample", **kwargs)
    with pytest.raises(ValueError):
        Manifest((ManifestEntry("a", 0), ManifestEntry("a", 0)))
    with pytest.raises(ValueError):
        Manifest(("bad",))
    assert scan(tmp_path) == Manifest(())
