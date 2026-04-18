"""Lightweight diagnostic endpoint for inspecting backend filesystem state.

Not for production use long-term — but invaluable when debugging
'file not found' / 'volume mounted?' questions on a remote deploy.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from app.routes.datasets import STORE


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/storage-info")
def storage_info() -> dict:
    """Report what the backend sees of its upload storage path + volume.

    Used to diagnose 'missing required CSV' errors: shows whether the
    persistent volume is actually mounted at /data, whether STORE resolves
    to the expected path, and what dataset folders/files exist.
    """
    info: dict = {
        "env_CMC_UPLOAD_DIR": os.environ.get("CMC_UPLOAD_DIR"),
        "STORE": str(STORE),
        "STORE_exists": STORE.exists(),
        "data_dir_exists": os.path.isdir("/data"),
        "data_contents": _safe_listdir(Path("/data")),
        "store_contents": _safe_listdir(STORE),
        "per_dataset": _inspect_datasets(STORE),
    }
    return info


def _safe_listdir(p: Path) -> list[str] | str:
    if not p.exists():
        return f"<does not exist: {p}>"
    try:
        return sorted(child.name for child in p.iterdir())
    except Exception as e:  # noqa: BLE001
        return f"<error: {type(e).__name__}: {e}>"


def _inspect_datasets(store: Path) -> list[dict]:
    """For each ds_N folder under STORE, list the filenames inside."""
    out: list[dict] = []
    if not store.exists():
        return out
    try:
        for entry in sorted(store.iterdir()):
            if not entry.is_dir() or not entry.name.startswith("ds_"):
                continue
            try:
                files = sorted(p.name for p in entry.iterdir() if p.is_file())
            except Exception as e:  # noqa: BLE001
                files = [f"<error: {type(e).__name__}: {e}>"]
            out.append({"dataset_folder": entry.name, "files": files})
    except Exception:  # noqa: BLE001
        pass
    return out
