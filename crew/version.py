"""Code-version fingerprint for every results row (task C0). Owner: Member C.

git_commit() is stored in the git_commit column of runs.csv. It is
  * the git commit hash (plus "-dirty" if tracked files were modified), when git is available, or
  * "src-<sha256 of the crew/*.py sources>[:12]" otherwise (no git on the laptop, or inside the submitted notebook).
The source fingerprint changes whenever any line of crew/*.py changes, so two rows with the same value were produced
by byte-identical code, with or without git.
"""
from __future__ import annotations

import functools
import glob
import hashlib
import os
import subprocess

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(PACKAGE_DIR)


def _normalised_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:                  # binary read (no text encoding involved)
        return fh.read().replace(b"\r\n", b"\n")  # git may check files out with CRLF on Windows


def file_sha256(path: str) -> str:
    """Fingerprint of an instance file (runs.csv column instance_sha256; also for MANIFEST.csv, task B9).
    Line endings are normalised, so the same file hashes the same on Windows and on Mac/Linux."""
    return hashlib.sha256(_normalised_bytes(path)).hexdigest()


def source_fingerprint() -> str:
    """SHA-256 over the crew/*.py files (sorted by name; line endings normalised so Windows == Mac/Linux)."""
    h = hashlib.sha256()
    for path in sorted(glob.glob(os.path.join(PACKAGE_DIR, "*.py"))):
        h.update(os.path.basename(path).encode("utf-8") + b"\0" + _normalised_bytes(path) + b"\0")
    return h.hexdigest()


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=REPO_DIR, capture_output=True, text=True, timeout=10, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


@functools.lru_cache(maxsize=1)
def git_commit() -> str:
    """Code version for runs.csv: git hash if possible, else the source fingerprint (cached per process)."""
    sha = _git("rev-parse", "HEAD")
    if sha:
        dirty = _git("status", "--porcelain", "--untracked-files=no")
        return sha + ("-dirty" if dirty else "")
    return "src-" + source_fingerprint()[:12]
