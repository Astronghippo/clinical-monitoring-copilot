# Demo talk track

## What the prototype shows

1. **Upload the protocol.** Claude extracts the Schedule of Assessments and
   I/E criteria into a structured `ProtocolSpec`. Show the study_id + count
   of visits and criteria rendered back to the UI.
2. **Upload the synthetic dataset.** Four CSVs shaped like SDTM (DM, SV, VS, EX).
   These include 5 known, seeded deviations.
3. **Run analysis.** Three analyzers execute. Total latency: ~15-30s for 20
   subjects on synthetic data.
4. **Review findings.** Each finding is clickable, shows the protocol citation,
   the exact data row it came from, and a confidence score.
5. **Show the benchmark.** Run `python3 backend/scripts/benchmark.py` to show
   precision and recall against the known ground truth.

## What to emphasize

- **Semantic protocol reasoning** — no rules engine hand-coded per study.
  The protocol is read once, reasoned over, and applied.
- **Citations on every finding** — no hallucinated deviations. If the model
  says something, it must point to where.
- **Deterministic where possible, LLM where necessary.** Visit windows are pure
  date math with 100% confidence. Completeness and eligibility are LLM-driven
  with confidence < 1.0.

## What to acknowledge

- 20 synthetic subjects, not 200 real ones. Real scale requires RAG + chunking.
- No audit log, no validation, no EDC connector. This is about demonstrating
  that the core reasoning works.
- The benchmark's denominator is 5 seeded deviations. A real validation set
  would have hundreds across multiple protocols.

## Common questions

- **"Can it read DICOM / ECG waveforms?"** Not in this prototype. The analyzer
  architecture accepts any structured CSV; richer binary formats would plug in
  via a new domain loader.
- **"How do you stop it from making things up?"** Every finding cites protocol
  and data locations. Deterministic checks (visit windows) carry confidence
  1.0; LLM-driven checks report lower confidence so reviewers triage them differently.
- **"What about 21 CFR Part 11?"** Out of scope for the prototype. Production
  would add an immutable audit log, authenticated users, and electronic signatures
  on finding closeout.
