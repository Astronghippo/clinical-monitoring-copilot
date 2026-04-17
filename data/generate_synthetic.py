"""Generate synthetic SDTM-shaped CSVs with seeded deviations."""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).parent / "synthetic"
OUT.mkdir(exist_ok=True)

# Visit schedule: nominal days from V1 baseline
VISITS = [
    ("V1", "Baseline",   0,   (0, 0),   ["Vitals", "Labs", "ECG"]),
    ("V2", "Week 2",     14,  (-2, 2),  ["Vitals", "Labs"]),
    ("V3", "Week 4",     28,  (-3, 3),  ["Vitals", "Labs", "ECG"]),
    ("V4", "Week 8",     56,  (-5, 5),  ["Vitals", "Labs"]),
    ("V5", "Week 12",    84,  (-7, 7),  ["Vitals", "Labs", "ECG"]),
]

N_SUBJECTS = 20
SITE_START = date(2025, 6, 1)

# ---- Seeded deviations (ground truth for benchmarking) ----
# (subject_id, kind, details)
SEEDED = [
    ("1004", "visit_window",  {"visit": "V3", "days_late": 5}),
    ("1007", "missing_proc",  {"visit": "V2", "procedure": "Labs"}),
    ("1012", "eligibility",   {"criterion": "E2", "reason": "HbA1c 11.2% exceeds exclusion cutoff 10.5%"}),
    ("1015", "visit_window",  {"visit": "V4", "days_early": 8}),
    ("1018", "missing_proc",  {"visit": "V5", "procedure": "ECG"}),
]
SEEDED_MAP = {s[0]: (s[1], s[2]) for s in SEEDED}

def subjects():
    return [str(1000 + i) for i in range(1, N_SUBJECTS + 1)]

def write_dm():
    with open(OUT / "dm.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["USUBJID", "SITEID", "AGE", "SEX", "RACE", "HBA1C_SCREEN", "RFSTDTC"])
        for sid in subjects():
            hba1c = 8.5 + random.uniform(-1.2, 1.2)
            if sid == "1012":
                hba1c = 11.2  # eligibility deviation
            start = SITE_START + timedelta(days=random.randint(0, 60))
            w.writerow([sid, "SITE01",
                        random.randint(35, 70),
                        random.choice(["M", "F"]),
                        "WHITE",
                        f"{hba1c:.1f}",
                        start.isoformat()])

def write_sv_and_vs_ex():
    sv = open(OUT / "sv.csv", "w", newline=""); sv_w = csv.writer(sv)
    vs = open(OUT / "vs.csv", "w", newline=""); vs_w = csv.writer(vs)
    ex = open(OUT / "ex.csv", "w", newline=""); ex_w = csv.writer(ex)
    sv_w.writerow(["USUBJID", "VISIT", "VISITNUM", "SVSTDTC"])
    vs_w.writerow(["USUBJID", "VISIT", "VSTESTCD", "VSORRES", "VSDTC"])
    ex_w.writerow(["USUBJID", "VISIT", "EXTRT", "EXDOSE", "EXDTC"])

    for idx, sid in enumerate(subjects()):
        start = SITE_START + timedelta(days=idx * 2)
        for (vid, vname, day, _win, procs) in VISITS:
            actual_day = day
            dev = SEEDED_MAP.get(sid)
            if dev and dev[0] == "visit_window" and dev[1]["visit"] == vid:
                actual_day = day + dev[1].get("days_late", 0) - dev[1].get("days_early", 0)
            visit_date = start + timedelta(days=actual_day)
            sv_w.writerow([sid, vname, int(vid[1:]), visit_date.isoformat()])

            # Procedures
            for proc in procs:
                if dev and dev[0] == "missing_proc" \
                        and dev[1]["visit"] == vid and dev[1]["procedure"] == proc:
                    continue  # skip — seeded missing procedure
                if proc in ("Vitals", "ECG", "Labs"):
                    testcd = {"Vitals": "SYSBP", "ECG": "ECGINT", "Labs": "HBA1C"}[proc]
                    val = {"SYSBP": random.randint(110, 145),
                           "ECGINT": random.randint(380, 440),
                           "HBA1C": round(8.0 + random.uniform(-1, 1), 1)}[testcd]
                    vs_w.writerow([sid, vname, testcd, val, visit_date.isoformat()])

            ex_w.writerow([sid, vname, "STUDYDRUG", 10, visit_date.isoformat()])

    sv.close(); vs.close(); ex.close()

def write_ground_truth():
    gt = [{"subject_id": s[0], "kind": s[1], **s[2]} for s in SEEDED]
    (OUT.parent / "ground_truth.json").write_text(json.dumps(gt, indent=2))

if __name__ == "__main__":
    write_dm()
    write_sv_and_vs_ex()
    write_ground_truth()
    print(f"Wrote synthetic data to {OUT}")
    print(f"Seeded {len(SEEDED)} deviations (see ground_truth.json)")
