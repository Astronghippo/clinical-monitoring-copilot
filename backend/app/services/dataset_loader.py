from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


_REQUIRED = ["dm.csv", "sv.csv", "vs.csv"]


@dataclass
class PatientDataset:
    """Holds SDTM-shaped DataFrames for a single trial dataset."""
    dm: pd.DataFrame
    sv: pd.DataFrame
    vs: pd.DataFrame
    ex: pd.DataFrame | None = None

    def subjects(self) -> list[str]:
        return sorted(self.dm["USUBJID"].astype(str).unique().tolist())

    def visits_for(self, subject_id: str) -> pd.DataFrame:
        return (
            self.sv[self.sv["USUBJID"].astype(str) == str(subject_id)]
            .sort_values("VISITNUM")
        )

    def procedures_at(self, subject_id: str, visit_name: str) -> list[str]:
        mask = (self.vs["USUBJID"].astype(str) == str(subject_id)) & (
            self.vs["VISIT"] == visit_name
        )
        return self.vs.loc[mask, "VSTESTCD"].unique().tolist()

    def demographics(self, subject_id: str) -> dict:
        row = self.dm[self.dm["USUBJID"].astype(str) == str(subject_id)]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()


def load_dataset(folder: str | Path) -> PatientDataset:
    """Load the required SDTM CSVs from a folder into a PatientDataset.

    Raises FileNotFoundError if any of dm.csv, sv.csv, or vs.csv is missing.
    ex.csv is optional.
    """
    folder = Path(folder)
    missing = [f for f in _REQUIRED if not (folder / f).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required CSVs: {missing}")

    def _read(name: str) -> pd.DataFrame:
        return pd.read_csv(folder / name, dtype={"USUBJID": str})

    ex = _read("ex.csv") if (folder / "ex.csv").exists() else None
    return PatientDataset(dm=_read("dm.csv"), sv=_read("sv.csv"), vs=_read("vs.csv"), ex=ex)
