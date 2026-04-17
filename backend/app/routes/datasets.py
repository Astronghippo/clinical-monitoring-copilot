from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Dataset
from app.schemas import DatasetOut


# In containers we mount /data; in local/test we fall back to the system temp dir.
_DEFAULT_STORE = Path("/data/uploads") if os.path.isdir("/data") else Path(tempfile.gettempdir()) / "cmc_uploads"
STORE = Path(os.environ.get("CMC_UPLOAD_DIR", str(_DEFAULT_STORE)))
STORE.mkdir(parents=True, exist_ok=True)


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetOut)
async def upload_dataset(
    name: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> Dataset:
    if not files:
        raise HTTPException(400, "No files uploaded")
    d = Dataset(name=name, storage_path="")
    db.add(d)
    db.commit()
    db.refresh(d)
    folder = STORE / f"ds_{d.id}"
    folder.mkdir(parents=True, exist_ok=True)
    for f in files:
        if not f.filename:
            continue
        target = folder / Path(f.filename).name
        with open(target, "wb") as out:
            shutil.copyfileobj(f.file, out)
    d.storage_path = str(folder)
    db.commit()
    db.refresh(d)
    return d
