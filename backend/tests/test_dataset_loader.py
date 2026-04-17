from pathlib import Path

import pytest

from app.services.dataset_loader import PatientDataset, load_dataset

FIX = Path(__file__).parent / "fixtures" / "mini_dataset"


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
