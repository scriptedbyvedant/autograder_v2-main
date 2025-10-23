# Evaluation Report – LLM AutoGrader (Mock Data)



## 1. Data Ingestion & ETL (`pages/1_upload_data.py`)

| Metric | Result | Notes |
| --- | --- | --- |
| Lecturer PDF parsing success | **96 %** | Based on 50 mock PDFs (existing “Professor” headings). No parsing regressions after UI terminology change. |
| Student submission coverage | **100 %** | ZIP/PDF ingestion created entries for every submission; validation caught missing answers. |
| Average ingest time | **2.8 s** | On a MacBook M1 simulation; includes RAG seeding step. |

**Next Step:** Build the golden dataset so future runs compare parsed JSON directly against ground truth and produce precision/recall values.

---

## 2. Grading Engine Performance

### 2.1 Accuracy vs Lecturer Benchmarks

| Assessment Type | Agreement with Lecturer | Comment |
| --- | --- | --- |
| Text responses | **91 %** | Dual LLM passes with RAG context kept variance low. |
| Code assignments | **88 %** | Partial credit awarded; remaining gap due to hidden-edge-unit tests. |
| Mathematical answers | **86 %** | Symbolic equivalence occasionally flagged as mismatch. |
| Multimodal tasks | **83 %** | OCR noise and context stitching reduce consistency. |

![Figure 1 – AI vs Lecturer Score Agreement](figure_accuracy.png)

### 2.2 Turnaround Efficiency

![Figure 2 – Turnaround Time Trend](figure_turnaround.png)

- **Baseline:** Manual process averaged ~96 hours per cohort.
- **AutoGrader Simulation:** Dropped to ~38 hours by week 8 thanks to automated parsing + grading.

### 2.3 Explainability & Human Review

| Check | Result | Notes |
| --- | --- | --- |
| Criteria editable | ✅ | Lecturer edits persisted to `grading_results`/`grading_corrections`. |
| Explanation regeneration | ✅ | On-demand prompts produced revised narrative aligned with new scores. |
| Audit logging | ✅ | All interventions captured in PostgreSQL with timestamps. |

---

## 3. Retrieval-Augmented Generation (RAG)

| Aspect | Status | Observation |
| --- | --- | --- |
| Seeding coverage | ✅ | Questions, criteria, and ideal answers embedded at upload. |
| Retrieval hit-rate (mock) | **78 %** | Similar answers retrieved for 39/50 sample questions. |
| Post-correction updates | ❌ | Not yet feeding lecturer corrections back into the vector store (planned feature). |

*Future Measurement:* Once correction sync is implemented, re-run RAG evaluation to report precision/recall of retrieved snippets.

---

## 4. Human-In-The-Loop Collaboration

| Scenario | Outcome |
| --- | --- |
| Score/feedback override | ✅ Saved to `new_score` / `new_feedback`, reflected on reload. |
| Sharing via collaboration centre | ✅ Shared record visible to recipient with read-only state. |
| Lecturer terminology review | ✅ UI relabelled to “Lecturer/Criteria” while preserving existing parsing. |

Outstanding enhancement: push corrected feedback into RAG embeddings.

---

## 5. Analytics & Reporting (`pages/3_dashboard.py`)

| KPI | Result | Comment |
| --- | --- | --- |
| Dashboard load & filters | ✅ No regressions on mock dataset after CSV/PDF export additions. |
| CSV export | ✅ Produces filtered dataset for offline analysis. |
| PDF export with charts | ✅ Kaleido rendering embeds every Plotly figure in report. |

![Figure 3 – Feature Usage Share](figure_usage.png)

Usage snapshot (mock pilot, n=120 lecturer sessions): 42 % of time spent on grading workflow, 28 % on analytics, 18 % on explanation tool, 12 % on collaboration.

---

## 6. Infrastructure & Deployment Readiness

| Item | Status | Action |
| --- | --- | --- |
| PostgreSQL schema bootstrap | ✅ | Auto-created grading tables on first run. |
| Fine-tuning assistant | ❌ Out of scope | Lecturer confirmed LoRA workflow can remain future work. |
| GCP architecture pilot | ⚠️ Pending | Plan to deploy Streamlit on Cloud Run + Cloud Functions + Cloud SQL as next milestone. |

---

## 7. Summary Action Plan

1. **Golden Dataset (High priority):** Curate lecturer-grade pairs for text, code, math, and multimodal questions; compute actual accuracy metrics.
2. **RAG Correction Sync:** Persist lecturer edits into the vector store; measure retrieval precision/recall after the update.
3. **Dashboard Regression Tests:** Add automated chart/CSV checks to CI to prevent analytics drift.
4. **Cloud Pilot:** Validate the proposed GCP deployment and gather performance metrics vs local setup.

---

## 8. Attachments

- `figure_accuracy.png`
- `figure_turnaround.png`
- `figure_usage.png`

These mock artefacts are stored in `evaluation_reports/` and can be regenerated with real data later.
