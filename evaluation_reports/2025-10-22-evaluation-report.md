# Evaluation Report — LLM AutoGrader (2025-10-22)

This document summarizes the verification activities performed ahead of the submission deadline. It follows the evaluation plan defined in `project_docs/EVALUATION.md`, highlighting what has been validated, what remains outstanding, and the recommended follow-up actions.

> **Important:** Due to time constraints and the absence of curated benchmark datasets, only lightweight checks were executed. The outstanding items below should be addressed in the next iteration.

---

## 1. Data Ingestion & ETL (`pages/1_upload_data.py`)

| Check | Status | Notes |
| --- | --- | --- |
| Parser smoke test on sample lecturer PDF | ✅ | Used an existing template (with "Professor" headings). Confirmed that parsing still succeeds after UI terminology changes. |
| Golden dataset regression | ⛔ Not executed | Requires curated lecturer/student PDFs with ground-truth JSON. Prepare fixtures and automate comparison with pytest. |

**Recommendation:** Prioritize building the golden dataset so we can report precision/recall of question/rubric extraction. Without it, downstream grading cannot be confidently validated.

---

## 2. Grading Engine

| Component | Status | Notes |
| --- | --- | --- |
| Text grading (`grader_engine/text_grader.py`) | ⚠️ Partially checked | Manual spot-check on a single artefact; no quantitative comparison vs lecturer scores yet. |
| Code grading (`grader_engine/code_grader.py`) | ⛔ Not executed | Lacks a sandboxed benchmark project with expected results. |
| Math grading (`grader_engine/math_grader.py`) | ⛔ Not executed | Need a small set of numeric/Latex questions with verified answers. |
| Multimodal grading (`grader_engine/multimodal_grader.py`) | ⛔ Not executed | Requires multimodal sample with expected output. |
| Multi-agent disagreement metrics | ⛔ Not collected | Current implementation runs redundant calls sequentially; consensus stats were not recorded. |

**Recommendation:** Assemble a 10–20 item evaluation set (text/code/math) with lecturer markings. Compare AI vs lecturer scores (MAE, % within tolerance) and capture qualitative feedback accuracy.

---

## 3. Retrieval & Explainability

| Check | Status | Notes |
| --- | --- | --- |
| RAG coverage (questions seeded into store) | ✅ | Verified during upload flow — vector store receives question/ideal/rubric blocks. |
| RAG effectiveness (retrieved examples relevance) | ⛔ Not measured | Need to log retrieved items and have lecturer rate relevance. |
| Explainability completeness (`generate_explanation`) | ⛔ Not measured | Requires rubric coverage checklist per evaluation plan. |

**Recommendation:** Export RAG retrieval logs for 5 grading sessions and have lecturers rate usefulness. For explanations, score whether each criterion is referenced (yielding the “Criteria Coverage” metric).

---

## 4. Human-in-the-Loop Workflow

| Check | Status | Notes |
| --- | --- | --- |
| Manual edits persisted (`update_grading_result_with_correction`) | ✅ | Smoke test: edited a score/feedback, verified update in DB via dashboard. |
| Collaboration sharing | ✅ | Shared a sample grading result with a colleague account; entry appeared in collaboration centre. |
| RAG refresh after correction | ⛔ Not implemented | Documented gap; corrections are not yet fed back into the retrieval store. |

**Recommendation:** Extend `rag_utils.py` to append corrections; then repeat the sharing/edit workflow and confirm that future gradings surface the updated examples.

---

## 5. Analytics & Reporting (`pages/3_dashboard.py`)

| Check | Status | Notes |
| --- | --- | --- |
| Dashboard filters & KPIs | ✅ | Manually exercised filters; no errors encountered. |
| Plot rendering | ✅ | All charts render; PDF export now includes figures. |
| CSV export | ✅ | Newly added “Download Filtered Data (CSV)” option validated. |
| Data integrity (sample audit) | ⚠️ Limited | Verified counts on a single dataset; no automated testing yet. |

**Recommendation:** Add dashboard regression tests (e.g., using saved CSV fixtures) to confirm chart data stays consistent after code changes.

---

## 6. Backend & Infrastructure

| Area | Status | Notes |
| --- | --- | --- |
| PostgreSQL CRUD helpers (`database/postgres_handler.py`) | ✅ | Existing unit tests cover inserts/updates for grading results/shares. |
| Fine-tuning pipeline | ❌ Out of scope | Confirmed with the lecturer that fine-tuning is not part of this delivery. |
| Cloud architecture readiness | ⚠️ Conceptual | Future-state GCP diagram updated, but no deployments performed. |

**Recommendation:** Schedule a follow-up to pilot the Cloud Run / Cloud Functions architecture and capture performance metrics vs local deployment.

---

## 7. Summary & Next Steps

### Completed
- Lecturer-facing terminology updates (UI) without breaking backend ingestion.
- Dashboard exports (PDF with figures, CSV) working as intended.
- Manual end-to-end smoke tests on upload → grading → review → export.

### Outstanding (High Priority)
1. **Golden Dataset & Parser Accuracy:** Build fixtures and automate evaluation with pytest.
2. **Grading Accuracy Benchmarks:** Create lecturer-graded reference set; compute MAE and qualitative match rates.
3. **RAG & Explanation Metrics:** Implement logging + lecturer review to quantify relevance/coverage.

### Outstanding (Medium Priority)
4. **Dashboard Regression Tests:** Automate validation of analytics outputs.
5. **Cloud Deployment Pilot:** Run the app on GCP to validate the proposed architecture and gather ops metrics.

---

## Appendix A – Quick Commands

```bash
# Run unit tests (parser/grading stubs)
pytest

# Export dashboard data (CSV via UI) for manual auditing
streamlit run pages/3_dashboard.py

# Capture grading cache for ad-hoc analysis
streamlit run pages/2_grading_result.py
```

This report will be updated once the missing datasets and benchmark runs are available. EOF
