from pathlib import Path

import pytest

from app.services.dataset_loader import (
    PatientDataset,
    load_dataset,
    normalize_visit_name,
)

FIX = Path(__file__).parent / "fixtures" / "mini_dataset"


# ---------- helper to build a throwaway dataset on disk ----------

def _write_dataset(tmp: Path, *, dm: str, sv: str, vs: str,
                   dm_name: str = "dm.csv", sv_name: str = "sv.csv",
                   vs_name: str = "vs.csv") -> Path:
    (tmp / dm_name).write_text(dm)
    (tmp / sv_name).write_text(sv)
    (tmp / vs_name).write_text(vs)
    return tmp


def test_load_dataset_returns_dataframes():
    ds = load_dataset(FIX)
    assert isinstance(ds, PatientDataset)
    assert set(ds.dm["USUBJID"].astype(str)) == {"1001", "1002", "1003"}
    assert len(ds.sv) == 3
    assert len(ds.vs) == 3


def test_subjects_helper():
    ds = load_dataset(FIX)
    assert ds.subjects() == ["1001", "1002", "1003"]


def test_visits_for_subject():
    ds = load_dataset(FIX)
    vs = ds.visits_for("1001")
    assert len(vs) == 2
    assert vs.iloc[0]["VISIT"] == "Baseline"


def test_procedures_at_visit():
    ds = load_dataset(FIX)
    procs = ds.procedures_at("1001", "Baseline")
    assert set(procs) == {"SYSBP", "HBA1C"}


def test_demographics_returns_row_dict():
    ds = load_dataset(FIX)
    demo = ds.demographics("1001")
    assert demo["USUBJID"] == "1001"
    assert float(demo["HBA1C_SCREEN"]) == 8.1


def test_missing_required_csv_raises():
    import tempfile
    import pathlib
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(FileNotFoundError):
            load_dataset(pathlib.Path(tmp))


# ---------- Resilience tests: column aliases ----------

def test_loader_accepts_snake_case_column_aliases(tmp_path):
    _write_dataset(
        tmp_path,
        dm=(
            "subject_id,site_id,age,gender,race,hba1c_base,start_date\n"
            "2001,S01,55,M,WHITE,8.1,2025-06-01\n"
        ),
        sv=(
            "subject_id,visit_name,visit_number,visit_date\n"
            "2001,Baseline,1,2025-06-01\n"
        ),
        vs=(
            "subject_id,visit_name,test_code,result,collection_date\n"
            "2001,Baseline,SYSBP,130,2025-06-01\n"
        ),
    )
    ds = load_dataset(tmp_path)
    # Columns got renamed to canonical.
    assert "USUBJID" in ds.dm.columns
    assert "VISIT" in ds.sv.columns
    assert "VSTESTCD" in ds.vs.columns
    assert ds.subjects() == ["2001"]
    # Demographics picked up the aliased HBA1C_SCREEN.
    demo = ds.demographics("2001")
    assert float(demo["HBA1C_SCREEN"]) == 8.1


def test_loader_is_case_insensitive_for_column_headers(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,SEX,HBA1C_SCREEN,RFSTDTC\n1001,55,M,8.1,2025-06-01\n",
        sv="usubjid,Visit,VisitNum,SVSTDTC\n1001,Baseline,1,2025-06-01\n",
        vs="USUBJID,VISIT,vstestcd,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,2025-06-01\n",
    )
    ds = load_dataset(tmp_path)
    assert ds.subjects() == ["1001"]
    assert "VSTESTCD" in ds.vs.columns


# ---------- Resilience tests: filename aliases ----------

def test_loader_accepts_filename_aliases(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,HBA1C_SCREEN,RFSTDTC\n1001,55,8.1,2025-06-01\n",
        sv="USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,2025-06-01\n",
        vs="USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,2025-06-01\n",
        dm_name="demographics.csv",
        sv_name="visits.csv",
        vs_name="vitals.csv",
    )
    ds = load_dataset(tmp_path)
    assert ds.subjects() == ["1001"]


def test_loader_is_case_insensitive_for_filenames(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,RFSTDTC\n1001,55,2025-06-01\n",
        sv="USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,2025-06-01\n",
        vs="USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,2025-06-01\n",
        dm_name="DM.CSV",
        sv_name="Sv.Csv",
        vs_name="VS.csv",
    )
    ds = load_dataset(tmp_path)
    assert ds.subjects() == ["1001"]


# ---------- Resilience tests: date normalization ----------

def test_loader_normalizes_us_format_dates_to_iso(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,RFSTDTC\n1001,55,06/01/2025\n",
        sv="USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,06/01/2025\n",
        vs="USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,06/01/2025\n",
    )
    ds = load_dataset(tmp_path)
    assert ds.sv.iloc[0]["SVSTDTC"] == "2025-06-01"
    assert ds.vs.iloc[0]["VSDTC"] == "2025-06-01"
    assert ds.dm.iloc[0]["RFSTDTC"] == "2025-06-01"


def test_loader_normalizes_sas_ddmmmyyyy_dates(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,RFSTDTC\n1001,55,01JUN2025\n",
        sv="USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,15JUN2025\n",
        vs="USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,15JUN2025\n",
    )
    ds = load_dataset(tmp_path)
    assert ds.sv.iloc[0]["SVSTDTC"] == "2025-06-15"
    assert ds.dm.iloc[0]["RFSTDTC"] == "2025-06-01"


def test_loader_leaves_none_for_unparseable_dates(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,RFSTDTC\n1001,55,not a date\n",
        sv="USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,2025-06-01\n",
        vs="USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n1001,Baseline,SYSBP,130,2025-06-01\n",
    )
    ds = load_dataset(tmp_path)
    assert ds.dm.iloc[0]["RFSTDTC"] is None


# ---------- Resilience tests: visit name fuzzy matching ----------

def test_normalize_visit_name_lowercases_and_collapses_whitespace():
    assert normalize_visit_name("Week  2") == "week 2"
    assert normalize_visit_name("  WEEK 2  ") == "week 2"
    assert normalize_visit_name("Week\t2") == "week 2"


def test_normalize_visit_name_handles_none_and_nan():
    import math
    assert normalize_visit_name(None) == ""
    assert normalize_visit_name(math.nan) == ""


# ---------- Wide-format single-CSV auto-detection + pivot ----------

def test_wide_format_single_csv_is_detected_and_pivoted(tmp_path):
    """One CSV with Subject_ID + Visit + Lab_* columns → auto-pivoted into SDTM."""
    # Looks like a Medidata Rave export row.
    content = (
        "Subject_ID,Site_ID,Age,Sex,Visit,Treatment_Arm,Dose_mg,"
        "Lab_ALT,Lab_AST,Lab_Hb\n"
        "S1000,US003,55,M,Week 4,Drug A,10,51.9,21.4,13.8\n"
        "S1001,EU001,49,F,Baseline,Drug B,0,17.1,21.7,14.2\n"
        "S1002,US001,70,M,Week 12,Drug A,20,30.0,22.0,11.9\n"
    )
    (tmp_path / "mock_rave_clinical_dataset.csv").write_text(content)

    ds = load_dataset(tmp_path)

    # DM: one row per subject.
    assert ds.subjects() == ["S1000", "S1001", "S1002"]
    assert set(ds.dm.columns) >= {"USUBJID", "SITEID", "AGE", "SEX"}
    # SV: one row per (subject, visit), VISITNUM derived from visit name.
    assert len(ds.sv) == 3
    sv_sorted = ds.sv.sort_values("USUBJID").reset_index(drop=True)
    assert sv_sorted.iloc[0]["VISITNUM"] == 4  # Week 4 → 4
    assert sv_sorted.iloc[1]["VISITNUM"] == 0  # Baseline → 0
    # VS: Lab_ALT / Lab_AST / Lab_Hb melted into VSTESTCD rows.
    assert len(ds.vs) == 9  # 3 labs × 3 subjects
    assert set(ds.vs["VSTESTCD"].unique()) == {"ALT", "AST", "HGB"}
    # EX: Dose_mg becomes EXDOSE with EXTRT carried from Treatment_Arm.
    assert ds.ex is not None
    assert len(ds.ex) == 3


def test_wide_format_demographics_accessible_by_subject(tmp_path):
    content = (
        "Subject_ID,Age,Sex,Visit,Lab_ALT\n"
        "S1000,55,M,Week 4,50.0\n"
    )
    (tmp_path / "data.csv").write_text(content)
    ds = load_dataset(tmp_path)
    demo = ds.demographics("S1000")
    assert demo["USUBJID"] == "S1000"
    assert int(demo["AGE"]) == 55


def test_wide_format_procedures_at_visit_returns_lab_codes(tmp_path):
    content = (
        "Subject_ID,Visit,Lab_ALT,Lab_Hb\n"
        "S1000,Baseline,10.0,14.0\n"
    )
    (tmp_path / "rave_export.csv").write_text(content)
    ds = load_dataset(tmp_path)
    procs = ds.procedures_at("S1000", "Baseline")
    assert set(procs) == {"ALT", "HGB"}


def test_wide_format_without_dose_or_labs_falls_through_to_error(tmp_path):
    """A CSV that's clearly not wide-format shouldn't be pivoted."""
    content = "col_a,col_b\n1,2\n"
    (tmp_path / "random.csv").write_text(content)
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path)


def test_procedures_at_visit_matches_case_insensitively(tmp_path):
    _write_dataset(
        tmp_path,
        dm="USUBJID,AGE,RFSTDTC\n1001,55,2025-06-01\n",
        sv="USUBJID,VISIT,VISITNUM,SVSTDTC\n1001,Baseline,1,2025-06-01\n",
        vs=(
            "USUBJID,VISIT,VSTESTCD,VSORRES,VSDTC\n"
            "1001,Baseline,SYSBP,130,2025-06-01\n"
            "1001,Baseline,HBA1C,8.1,2025-06-01\n"
        ),
    )
    ds = load_dataset(tmp_path)
    # All three of these queries should return the same result.
    assert set(ds.procedures_at("1001", "Baseline")) == {"SYSBP", "HBA1C"}
    assert set(ds.procedures_at("1001", "baseline")) == {"SYSBP", "HBA1C"}
    assert set(ds.procedures_at("1001", "BASELINE")) == {"SYSBP", "HBA1C"}
    assert set(ds.procedures_at("1001", "  Baseline  ")) == {"SYSBP", "HBA1C"}
