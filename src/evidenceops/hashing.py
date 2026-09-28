"""Streaming SHA-256 enrichment and read-only verification."""

import hashlib
import os
import stat
from dataclasses import replace
from pathlib import Path

from .manifest import Manifest, _parent


def _digest(root: str | Path, relative: str) -> tuple[str, int]:
    with _parent(root, relative) as (parent, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("Hashing requires a regular file")
            digest = hashlib.sha256()
            while chunk := stream.read(65536):
                digest.update(chunk)
            after = os.fstat(stream.fileno())
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            if any(getattr(before, field) != getattr(after, field) for field in fields) or (
                current.st_dev,
                current.st_ino,
            ) != (after.st_dev, after.st_ino):
                raise RuntimeError("File changed during hashing")
            return digest.hexdigest(), after.st_size


def sha256_file(path: str | Path) -> str:
    """Hash a regular file in 64 KiB chunks without following symlinks."""
    path = Path(path)
    return _digest(path.parent, path.name)[0]


def enrich_manifest(manifest: Manifest, root: str | Path) -> Manifest:
    """Return a new snapshot; reject size changes since the original scan."""
    entries = []
    for entry in manifest.entries:
        if entry.kind == "symlink":
            entries.append(entry)
            continue
        digest, size = _digest(root, entry.path)
        if size != entry.size:
            raise RuntimeError("File size changed since scan")
        entries.append(replace(entry, sha256=digest))
    return Manifest(tuple(entries))


def verify_manifest(manifest: Manifest, root: str | Path) -> dict[str, str]:
    """Verify listed entries only; symlink OK means matching kind and size only.

    Unhashed regular files raise ValueError. Unsafe paths, I/O failures and
    concurrent changes propagate; they must never be interpreted as success.
    """
    if any(entry.kind == "file" and entry.sha256 is None for entry in manifest.entries):
        raise ValueError("Verification requires hashes for every regular file")
    results = {}
    for entry in manifest.entries:
        try:
            with _parent(root, entry.path) as (parent, name):
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            correct_kind = (
                stat.S_ISLNK(info.st_mode)
                if entry.kind == "symlink"
                else stat.S_ISREG(info.st_mode)
            )
            if not correct_kind:
                status = "HASH_MISMATCH"
            elif info.st_size != entry.size:
                status = "SIZE_MISMATCH"
            elif entry.kind == "symlink":
                status = "OK"
            else:
                digest, size = _digest(root, entry.path)
                status = (
                    "SIZE_MISMATCH"
                    if size != entry.size
                    else ("OK" if digest == entry.sha256 else "HASH_MISMATCH")
                )
        except FileNotFoundError:
            status = "MISSING"
        results[entry.path] = status
    return results
