"""Deterministic snapshots; symlinks are represented, never traversed."""

import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


def _parts(path: str) -> tuple[str, ...]:
    if not isinstance(path, str) or not path or "\\" in path or ":" in path or "\0" in path:
        raise ValueError("Expected a canonical relative POSIX path")
    parts = tuple(path.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Expected a canonical relative POSIX path")
    return parts


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size: int
    sha256: str | None = None
    kind: str = "file"

    def __post_init__(self):
        _parts(self.path)
        if type(self.size) is not int or self.size < 0:
            raise ValueError("Size must be a nonnegative integer")
        if self.kind not in ("file", "symlink"):
            raise ValueError("Unsupported entry kind")
        if self.sha256 is not None and (
            not isinstance(self.sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None
            or self.kind == "symlink"
        ):
            raise ValueError("Invalid SHA-256 digest")


@dataclass(frozen=True)
class Manifest:
    entries: tuple[ManifestEntry, ...]

    def __post_init__(self):
        entries = tuple(self.entries)
        if any(not isinstance(entry, ManifestEntry) for entry in entries):
            raise ValueError("Expected manifest entries")
        if len({entry.path for entry in entries}) != len(entries):
            raise ValueError("Duplicate entry path")
        object.__setattr__(self, "entries", tuple(sorted(entries, key=lambda entry: entry.path)))


@contextmanager
def _directory(path: str | Path):
    """Open each directory component without following links (POSIX only)."""
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW"):
        raise NotImplementedError("Safe filesystem reads require POSIX O_NOFOLLOW")
    path = Path(path)
    if ".." in path.parts:
        raise ValueError("Parent directory traversal is prohibited")
    fd = os.open(path.anchor or ".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:] if path.is_absolute() else path.parts:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _parent(root: str | Path, relative: str):
    parts = _parts(relative)
    with _directory(root) as root_fd:
        fd = os.dup(root_fd)
        try:
            for part in parts[:-1]:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            yield fd, parts[-1]
        finally:
            os.close(fd)


def scan(root: str | Path, follow_symlinks: bool = False) -> Manifest:
    """Scan regular files and link metadata; fail on unsupported special files."""
    if follow_symlinks is not False:
        raise ValueError("Following symlinks is not supported")
    entries = []

    def visit(fd, prefix=""):
        for name in sorted(os.listdir(fd)):
            relative = f"{prefix}{name}"
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                entries.append(ManifestEntry(relative, info.st_size, kind="symlink"))
            elif stat.S_ISREG(info.st_mode):
                entries.append(ManifestEntry(relative, info.st_size))
            elif stat.S_ISDIR(info.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    visit(child, relative + "/")
                finally:
                    os.close(child)
            else:
                raise ValueError("Special filesystem entries are unsupported")

    with _directory(root) as fd:
        visit(fd)
    return Manifest(tuple(entries))
