"""Resilient SDTM-shaped dataset loader.

Accepts:
- Canonical SDTM filenames (dm.csv, sv.csv, vs.csv, ex.csv) AND common aliases
  (demographics.csv, visits.csv, vitals.csv, exposure.csv, etc.) — all case-insensitive.
- Canonical SDTM column names (USUBJID, VISIT, VISITNUM, SVSTDTC, …) AND common
  aliases (subject_id, visit_name, visit_date, result, …) — case-insensitive.
- Multiple date formats (ISO, US, European, SAS DD-MMM-YYYY); all normalized
  to ISO `YYYY-MM-DD` strings so downstream analyzers can assume one shape.
- Visit name variations (whitespace, case) via `normalize_visit_name`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


# ---------- Column name aliasing ----------

# Canonical SDTM column → list of accepted aliases (compared case-insensitively after stripping).
_COLUMN_ALIASES: dict[str, list[str]] = {
    "USUBJID": [
        "usubjid", "subject_id", "subjid", "subj_id", "patient_id", "patientid",
        "subject", "subject id", "patient",
    ],
    "VISIT": ["visit", "visit_name", "visitname", "visit_label", "visit name"],
    "VISITNUM": [
        "visitnum", "visit_num", "visit_number", "visit_seq", "sequence",
        "visit_n", "visit_no",
    ],
    "SVSTDTC": [
        "svstdtc", "visit_date", "visitdate", "date_of_visit", "svdate",
        "actual_date", "visit_dt",
    ],
    "VSTESTCD": [
        "vstestcd", "test_code", "testcode", "parameter_code", "param_code",
        "code", "test", "param",
    ],
    "VSORRES": [
        "vsorres", "result", "value", "vsres", "observation", "test_result",
        "measurement",
    ],
    "VSDTC": ["vsdtc", "collection_date", "obs_date", "measurement_date"],
    "SITEID": ["siteid", "site_id", "site", "center", "centre"],
    "AGE": ["age", "subject_age"],
    "SEX": ["sex", "gender"],
    "RACE": ["race", "ethnicity"],
    "HBA1C_SCREEN": [
        "hba1c_screen", "hba1c_screening", "screen_hba1c", "hba1c_base",
        "baseline_hba1c",
    ],
    "RFSTDTC": [
        "rfstdtc", "study_start", "start_date", "enrollment_date",
        "rfstartdtc", "first_dose_date",
    ],
    "EXTRT": ["extrt", "treatment", "drug", "medication"],
    "EXDOSE": ["exdose", "dose", "dosage"],
    "EXDTC": ["exdtc", "dose_date", "administration_date", "dosing_date"],
}

# Reverse index: lower-alias → canonical column name.
_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias.lower(): canonical
    for canonical, aliases in _COLUMN_ALIASES.items()
    for alias in aliases
}


# ---------- Filename aliasing ----------

# Canonical short-name → list of accepted filenames (case-insensitive).
_FILE_ALIASES: dict[str, list[str]] = {
    "dm": ["dm.csv", "demographics.csv", "subjects.csv", "subject_demographics.csv", "dm.xls", "dm.xlsx"],
    "sv": ["sv.csv", "visits.csv", "subject_visits.csv", "visit_schedule.csv", "sv.xlsx"],
    "vs": [
        "vs.csv", "vitals.csv", "vital_signs.csv", "observations.csv",
        "measurements.csv", "labs.csv", "vs.xlsx",
    ],
    "ex": ["ex.csv", "exposure.csv", "dosing.csv", "administrations.csv", "ex.xlsx"],
}

# Which columns in each domain hold dates (to normalize to ISO on load).
_DATE_COLS_BY_DOMAIN: dict[str, list[str]] = {
    "dm": ["RFSTDTC"],
    "sv": ["SVSTDTC"],
    "vs": ["VSDTC"],
    "ex": ["EXDTC"],
}


# ---------- Public helpers ----------

def normalize_visit_name(name) -> str:
    """Lowercase + collapse whitespace so 'Week 2', 'week  2', 'WEEK 2' all match.

    Returns '' for None/NaN/empty.
    """
    if name is None:
        return ""
    try:
        if pd.isna(name):  # handles float NaN
            return ""
    except (TypeError, ValueError):
        pass
    return " ".join(str(name).strip().lower().split())


# ---------- Normalization internals ----------

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename any aliased columns to their canonical SDTM names."""
    rename_map: dict[str, str] = {}
    for actual in df.columns:
        key = str(actual).strip().lower()
        canonical = _ALIAS_TO_CANONICAL.get(key)
        if canonical and canonical != actual:
            rename_map[actual] = canonical
    return df.rename(columns=rename_map) if rename_map else df


def _normalize_dates(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Convert date-ish columns to ISO `YYYY-MM-DD` strings (preserves NaN as None).

    Tries three passes in order: standard parsing, US dayfirst=False, EU dayfirst=True.
    Anything still unparseable becomes None.
    """
    for col in cols:
        if col not in df.columns:
            continue
        raw = df[col]
        # Pass 1: pandas default (handles ISO, natural formats, datetime objects)
        parsed = pd.to_datetime(raw, errors="coerce")
        # Pass 2: dayfirst=True for European dates (e.g. "15/06/2025")
        still_null = parsed.isna() & raw.notna() & (raw.astype(str).str.strip() != "")
        if still_null.any():
            fallback = pd.to_datetime(raw[still_null], errors="coerce", dayfirst=True)
            parsed = parsed.where(~still_null, fallback)
        # Emit ISO date strings; keep Nones where unparseable.
        df[col] = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), None)
    return df


def _find_file(folder: Path, short: str) -> Path | None:
    """Locate a CSV for the given short domain (dm/sv/vs/ex) by any known alias.

    Matches are case-insensitive and take the first hit in the file-alias list order.
    """
    try:
        entries = [p for p in folder.iterdir() if p.is_file()]
    except (FileNotFoundError, NotADirectoryError):
        return None
    lower_to_path = {p.name.lower(): p for p in entries}
    for alias in _FILE_ALIASES.get(short, []):
        hit = lower_to_path.get(alias.lower())
        if hit is not None:
            return hit
    return None


# ---------- Dataset API ----------

@dataclass
class PatientDataset:
    """Holds SDTM-shaped DataFrames with columns already renamed to canonical SDTM names."""
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
        """Fuzzy visit match: case + whitespace normalized."""
        target = normalize_visit_name(visit_name)
        visits_norm = self.vs["VISIT"].map(normalize_visit_name)
        mask = (self.vs["USUBJID"].astype(str) == str(subject_id)) & (visits_norm == target)
        return self.vs.loc[mask, "VSTESTCD"].unique().tolist()

    def demographics(self, subject_id: str) -> dict:
        row = self.dm[self.dm["USUBJID"].astype(str) == str(subject_id)]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()


def load_dataset(folder: str | Path) -> PatientDataset:
    """Load the required SDTM CSVs from `folder` into a PatientDataset.

    Required domains: dm, sv, vs. Optional: ex. Filenames and columns are matched
    case-insensitively against known aliases.

    Raises FileNotFoundError if any required domain file is missing.
    """
    folder = Path(folder)
    paths = {short: _find_file(folder, short) for short in ("dm", "sv", "vs", "ex")}

    missing = [short for short in ("dm", "sv", "vs") if paths[short] is None]
    if missing:
        accepted = {short: _FILE_ALIASES[short] for short in missing}
        raise FileNotFoundError(
            f"Missing required CSV(s): {missing}. "
            f"Accepted filenames (case-insensitive): {accepted}"
        )

    def _read(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path)
        df = _normalize_columns(df)
        if "USUBJID" in df.columns:
            df["USUBJID"] = df["USUBJID"].astype(str)
        return df

    dm = _normalize_dates(_read(paths["dm"]), _DATE_COLS_BY_DOMAIN["dm"])
    sv = _normalize_dates(_read(paths["sv"]), _DATE_COLS_BY_DOMAIN["sv"])
    vs = _normalize_dates(_read(paths["vs"]), _DATE_COLS_BY_DOMAIN["vs"])
    ex = (
        _normalize_dates(_read(paths["ex"]), _DATE_COLS_BY_DOMAIN["ex"])
        if paths["ex"] is not None
        else None
    )

    return PatientDataset(dm=dm, sv=sv, vs=vs, ex=ex)
