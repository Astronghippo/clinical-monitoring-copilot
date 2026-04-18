"""Resilient SDTM-shaped dataset loader.

Accepts:
- Canonical SDTM filenames (dm.csv, sv.csv, vs.csv, ex.csv) AND common aliases
  (demographics.csv, visits.csv, vitals.csv, exposure.csv, etc.) — all case-insensitive.
- Canonical SDTM column names (USUBJID, VISIT, VISITNUM, SVSTDTC, …) AND common
  aliases (subject_id, visit_name, visit_date, result, …) — case-insensitive.
- Multiple date formats (ISO, US, European, SAS DD-MMM-YYYY); all normalized
  to ISO `YYYY-MM-DD` strings so downstream analyzers can assume one shape.
- Visit name variations (whitespace, case) via `normalize_visit_name`.
- Single-file "wide" exports (e.g. Medidata Rave): one CSV with one row per
  subject-visit containing demographics + lab values + dose + visit all pivoted
  into a single row. The loader auto-detects this shape and melts it into the
  four SDTM domains internally.
"""
from __future__ import annotations

import re
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


# ---------- Wide-format single-CSV auto-detection + pivot ----------


def _looks_like_wide_format(df: pd.DataFrame) -> bool:
    """Return True if a single DataFrame looks like a Medidata-Rave-style export:
    one row per subject-visit with demographics, lab values, dose, etc. all
    pivoted onto the same row."""
    if df.empty:
        return False
    has_subject = "USUBJID" in df.columns
    has_visit = "VISIT" in df.columns
    has_lab_columns = any(c.startswith("Lab_") for c in df.columns)
    # A signature wide-format file has subject + visit and either Lab_* columns
    # OR a Dose_mg column indicating per-visit dosing detail.
    has_dose = any(c.lower() in ("dose_mg", "exdose", "dose") for c in df.columns)
    return has_subject and has_visit and (has_lab_columns or has_dose)


def _visit_name_to_num(name) -> int:
    """Derive a sortable VISITNUM from a visit name like 'Week 4' or 'Baseline'."""
    if name is None:
        return 999
    s = str(name).strip().lower()
    if not s:
        return 999
    if "baseline" in s or "screening" in s or s in ("bl", "scr"):
        return 0
    m = re.search(r"\d+", s)
    if m:
        return int(m.group())
    return 999  # unknown / unorderable


# Column-name (after normalization) → canonical VSTESTCD code.
# Handles the "Lab_*" style: Lab_Hb → HGB, Lab_ALT → ALT, etc.
_LAB_COLUMN_TO_TESTCODE: dict[str, str] = {
    "lab_alt": "ALT", "lab_ast": "AST", "lab_hgb": "HGB", "lab_hb": "HGB",
    "lab_hba1c": "HBA1C", "lab_gluc": "GLUC", "lab_glucose": "GLUC",
    "lab_creat": "CREAT", "lab_creatinine": "CREAT", "lab_wbc": "WBC",
    "lab_rbc": "RBC", "lab_plat": "PLAT", "lab_platelet": "PLAT",
    "lab_bun": "BUN", "lab_na": "NA", "lab_k": "K", "lab_cl": "CL",
    "lab_ca": "CA", "lab_alb": "ALB", "lab_tbili": "TBILI", "lab_crp": "CRP",
}


def pivot_wide_format(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    """Pivot a wide-format DataFrame into (dm, sv, vs, ex) SDTM DataFrames.

    Best-effort — fills in whatever it can from the columns present and leaves
    domains sparse rather than raising. Assumes `df` has already been column-
    normalized (USUBJID, VISIT, AGE, etc.).
    """
    df = df.copy()
    if "USUBJID" in df.columns:
        df["USUBJID"] = df["USUBJID"].astype(str)

    # --- DM: one row per subject with demographic columns ---
    dm_candidate_cols = ["USUBJID", "SITEID", "AGE", "SEX", "RACE", "HBA1C_SCREEN", "RFSTDTC"]
    # Carry along any non-standard but useful columns (e.g., Treatment_Arm, Efficacy_Response)
    extras_for_dm = [c for c in df.columns
                     if c not in dm_candidate_cols
                     and c not in ("VISIT", "VISITNUM", "SVSTDTC", "VSTESTCD", "VSORRES", "VSDTC", "EXTRT", "EXDOSE", "EXDTC")
                     and not c.startswith("Lab_")
                     and c.upper() not in ("ADVERSE_EVENT", "AE_SEVERITY", "DOSE_MG", "PROTOCOL_DEVIATION", "EFFICACY_RESPONSE", "TREATMENT_ARM")]
    dm_cols = [c for c in dm_candidate_cols + extras_for_dm if c in df.columns]
    if "USUBJID" in df.columns:
        dm = df[dm_cols].drop_duplicates(subset=["USUBJID"]).reset_index(drop=True)
    else:
        dm = pd.DataFrame(columns=dm_cols)

    # --- SV: one row per (USUBJID, VISIT) with visit metadata ---
    sv_cols = [c for c in ["USUBJID", "VISIT", "VISITNUM", "SVSTDTC"] if c in df.columns]
    sv = (
        df[sv_cols].drop_duplicates(subset=[c for c in ("USUBJID", "VISIT") if c in sv_cols])
        .reset_index(drop=True)
    )
    if "VISITNUM" not in sv.columns and "VISIT" in sv.columns:
        sv["VISITNUM"] = sv["VISIT"].map(_visit_name_to_num)

    # --- VS: melt Lab_* columns into long form ---
    lab_columns = [c for c in df.columns if c.startswith("Lab_")]
    if lab_columns and "USUBJID" in df.columns and "VISIT" in df.columns:
        id_vars = ["USUBJID", "VISIT"]
        if "SVSTDTC" in df.columns:
            id_vars.append("SVSTDTC")
        melted = df[id_vars + lab_columns].melt(
            id_vars=id_vars, value_vars=lab_columns,
            var_name="VSTESTCD", value_name="VSORRES",
        )
        # Map the lab column names to canonical testcodes (case-insensitive).
        melted["VSTESTCD"] = melted["VSTESTCD"].map(
            lambda c: _LAB_COLUMN_TO_TESTCODE.get(str(c).lower(), str(c).replace("Lab_", "").upper())
        )
        if "SVSTDTC" in id_vars:
            melted = melted.rename(columns={"SVSTDTC": "VSDTC"})
        else:
            melted["VSDTC"] = None
        # Drop rows with missing values (no observation = not captured)
        melted = melted.dropna(subset=["VSORRES"]).reset_index(drop=True)
        vs = melted[["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"]]
    else:
        vs = pd.DataFrame(columns=["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])

    # --- EX: one row per (USUBJID, VISIT) with dose ---
    ex: pd.DataFrame | None = None
    dose_col = next((c for c in df.columns if c.upper() == "DOSE_MG" or c == "EXDOSE"), None)
    if dose_col and "USUBJID" in df.columns and "VISIT" in df.columns:
        ex_cols = ["USUBJID", "VISIT", dose_col]
        if "SVSTDTC" in df.columns:
            ex_cols.append("SVSTDTC")
        ex = df[ex_cols].rename(columns={dose_col: "EXDOSE"})
        if "SVSTDTC" in ex.columns:
            ex = ex.rename(columns={"SVSTDTC": "EXDTC"})
        ex["EXTRT"] = df.get("Treatment_Arm", "STUDYDRUG")
        ex = ex.reset_index(drop=True)

    return dm, sv, vs, ex


def load_dataset(folder: str | Path) -> PatientDataset:
    """Load the required SDTM CSVs from `folder` into a PatientDataset.

    Two accepted shapes:
    1. Split SDTM format: separate dm.csv / sv.csv / vs.csv (+ optional ex.csv).
       Filenames and columns are matched case-insensitively against known aliases.
    2. Single-file wide format: one CSV containing Subject_ID + Visit + per-visit
       demographics and Lab_* columns (typical of Medidata Rave exports).
       Auto-detected and pivoted into the four SDTM domains in memory.

    Raises FileNotFoundError if the folder has no usable CSV.
    """
    folder = Path(folder)

    def _read(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path)
        df = _normalize_columns(df)
        if "USUBJID" in df.columns:
            df["USUBJID"] = df["USUBJID"].astype(str)
        return df

    # --- Split-format path (preferred when multiple files present) ---
    paths = {short: _find_file(folder, short) for short in ("dm", "sv", "vs", "ex")}
    split_missing = [short for short in ("dm", "sv", "vs") if paths[short] is None]

    if not split_missing:
        dm = _normalize_dates(_read(paths["dm"]), _DATE_COLS_BY_DOMAIN["dm"])
        sv = _normalize_dates(_read(paths["sv"]), _DATE_COLS_BY_DOMAIN["sv"])
        vs = _normalize_dates(_read(paths["vs"]), _DATE_COLS_BY_DOMAIN["vs"])
        ex = (
            _normalize_dates(_read(paths["ex"]), _DATE_COLS_BY_DOMAIN["ex"])
            if paths["ex"] is not None
            else None
        )
        return PatientDataset(dm=dm, sv=sv, vs=vs, ex=ex)

    # --- Wide-format path (one CSV in folder, shape looks unified) ---
    csvs: list[Path] = []
    try:
        csvs = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".csv"]
    except (FileNotFoundError, NotADirectoryError):
        csvs = []

    if len(csvs) == 1:
        wide = _read(csvs[0])
        if _looks_like_wide_format(wide):
            # Treat SVSTDTC column if present as a date column; normalize.
            wide = _normalize_dates(wide, ["SVSTDTC"])
            dm, sv, vs, ex = pivot_wide_format(wide)
            return PatientDataset(dm=dm, sv=sv, vs=vs, ex=ex)

    # --- Fall through to the original error if nothing matched ---
    accepted = {short: _FILE_ALIASES[short] for short in split_missing}
    raise FileNotFoundError(
        f"Missing required CSV(s): {split_missing}. "
        f"Accepted filenames (case-insensitive): {accepted}. "
        f"OR upload a single wide-format CSV with Subject_ID + Visit + Lab_* columns "
        f"(e.g. a Medidata Rave export)."
    )
