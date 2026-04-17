# Clinical Monitoring Copilot (Prototype)

A prototype that takes a clinical trial protocol (PDF) and a patient dataset
(SDTM-shaped CSVs) and surfaces protocol deviations across three analyzers:

- **Visit windows** — deterministic date math against the Schedule of Assessments
- **Procedure completeness** — Claude-reasoned check that required procedures were captured
- **Eligibility** — Claude-reasoned check that enrolled subjects meet inclusion/exclusion criteria

Every finding cites the exact protocol section and data row behind it.

## Quickstart

```bash
# 1. Configure
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY

# 2. Generate synthetic data (requires local Python + pypdf/reportlab)
python3 data/generate_synthetic.py

# 3. Boot the stack
docker compose up --build

# 4. Open http://localhost:3000
```

## Project layout

- `backend/` — FastAPI, SQLAlchemy, Claude-driven analyzers
- `frontend/` — Next.js 14 App Router + Tailwind
- `data/` — synthetic SDTM generator + seeded ground truth
- `backend/scripts/benchmark.py` — precision/recall against seeded deviations
- `docs/DEMO.md` — talk track for showing this to a data manager or CRA

## Running tests

Backend:

```bash
cd backend && PYTHONPATH=. python3 -m pytest
```

Frontend:

```bash
cd frontend && npm install && npm test
```

## Running the benchmark

With an Anthropic API key configured:

```bash
cd /path/to/clinical-monitoring-copilot
python3 backend/scripts/benchmark.py
```

Without an API key (only visit-window findings are real; LLM analyzers return stub no-ops):

```bash
python3 backend/scripts/benchmark.py --dry-run
```

## What's NOT in this prototype (by design)

- Authentication / multi-tenancy
- Audit log / 21 CFR Part 11 controls
- Real EDC connectors (Medidata / Veeva / Oracle)
- Validation package (GAMP 5 / CSA)

These are intentional cuts to ship a working demo fast. See `docs/DEMO.md`
for the talk track when showing this to a data manager or CRA.