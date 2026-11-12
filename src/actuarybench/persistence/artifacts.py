"""Local content-addressed artifact store for run reproducibility (prototype).

Layout: ``<root>/objects/<sha[:2]>/<sha256><suffix>``. An object's name *is* the SHA-256 of
its bytes, so any change to a stored file is detectable. Objects are written once (atomic
rename) and marked read-only; identical content is stored once and shared between runs.

This is a local, single-user design. It provides tamper *evidence*, not access control or
encryption, and is not suitable for sensitive insurer data in production.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Literal

from actuarybench.utils.hashing import sha256_bytes

ArtifactStatus = Literal["OK", "MISSING", "CORRUPTED"]


class ArtifactError(RuntimeError):
    pass


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def path_for(self, ref: dict) -> Path:
        sha = ref["sha256"]
        return self.root / "objects" / sha[:2] / f"{sha}{ref.get('suffix', '')}"

    def put(self, data: bytes, suffix: str) -> dict:
        """Store bytes; return a reference ``{sha256, suffix, bytes}``."""
        ref = {"sha256": sha256_bytes(data), "suffix": suffix, "bytes": len(data)}
        path = self.path_for(ref)
        if path.exists() and self.check(ref) == "OK":
            return ref
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():  # corrupted copy: replace it
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
            path.unlink()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        os.chmod(path, stat.S_IREAD)
        return ref

    def check(self, ref: dict | None) -> ArtifactStatus:
        if not ref:
            return "MISSING"
        path = self.path_for(ref)
        if not path.is_file():
            return "MISSING"
        return "OK" if sha256_bytes(path.read_bytes()) == ref["sha256"] else "CORRUPTED"

    def read(self, ref: dict | None) -> bytes:
        status = self.check(ref)
        if status != "OK":
            name = ref["sha256"][:12] if ref else "(none)"
            raise ArtifactError(f"Artifact {name} is {status}.")
        return self.path_for(ref).read_bytes()
