# Evaluation Strategy (Current Toolkit)

This document outlines practical evaluation steps that can be run with the dependencies already present in `requirements.txt`. Advanced ideas that rely on extra libraries are listed as optional enhancements.

---

## 1. Data Ingestion & Parsing (`pages/1_upload_data.py`)

**Goal:** Ensure professor PDFs and student submissions are parsed into the normalized session format without silently dropping content.

**Recommended Approach:**

1. Build a golden dataset of PDF fixtures (professor rubric, single-student PDF, multi-student PDF, ILIAS ZIP).
2. Write `pytest` tests that feed each fixture through `extract_multimodal_content_from_pdf`, `parse_professor_pdf`, and `parse_student_pdf`.
3. Compare outputs to expected JSON structures stored alongside the fixtures.

**Metrics:** Match percentage on questions, rubric entries, and answer count. Fail the test if any section is missing or misaligned.

---

## 2. Grading Engine Regression

**Goal:** Detect prompt drift or schema regressions in the text/multi-modal graders.

**Recommended Approach:**

1. Mock Ollama responses by monkeypatching `ChatOllama.invoke` (or by seeding a lightweight local model) to return deterministic payloads.
2. Run `grade_block` on representative question types (text, code, math) and assert:
   * `rubric_scores` length and keys match expectations.
   * `total` equals the sum of per-criterion scores.
   * `needs_review` flags only trigger when disagreement thresholds are crossed.

3. Validate serialization logic by persisting to an in-memory PostgreSQL instance or by mocking `PostgresHandler` methods.

---

## 3. Human-in-the-Loop Flow

**Goal:** Guarantee manual edits persist correctly and audit trails are maintained.

**Recommended Approach:**

1. Seed `grading_results` with a fixture row.
2. Call `update_grading_result_with_correction` and assert that:
   * `grading_results.new_score/new_feedback` update as expected.
   * A corresponding row appears in `grading_corrections` with matching timestamps and editor ID.
3. Validate `share_result`, `revoke_share`, and listing helpers with simple Postgres fixtures.

---

## 4. Dashboard Data Integrity

**Goal:** Ensure analytics visuals operate on correctly typed columns and never crash on sparse data.

**Recommended Approach:**

1. Unit test helper functions (`infer_question_type`, `calendar_heatmap`) to confirm graceful handling of missing or unexpected values.
2. For integration testing, provide a minimal `DataFrame` fixture to the dashboard functions and verify that generated figures have non-empty traces.
3. Exercise the CSV and PDF export helpers and confirm output files contain the requested filters.

---

## 5. Optional Enhancements (Require Extra Dependencies)

The following ideas remain valuable but would need new dependencies added to `requirements.txt`:

* **DeepEval / Ragas:** Semantic evaluation of feedback quality and rubric coverage.
* **SciPy / NumPy Statistics:** Quantify score error (MAE) and correlation against human-scored benchmarks.
* **simpledorff:** Compute Krippendorff's alpha across multiple graders for reliability studies.

If you adopt any of these, document the setup in the repository and extend the automated test suite accordingly.

---

## 6. Manual QA Checklist

* Upload professor PDF → verify question/rubric preview.
* Upload sample student PDFs/ZIP → confirm validation catches missing answers.
* Run grading on a known assignment → inspect rubric table, download feedback ZIP.
* Edit scores and feedback → ensure changes persist after page refresh (requires reloading session with cached results).
* Share a result and confirm it appears for the target professor in the collaboration center.
* Navigate the dashboard filters → confirm plots update and exports download successfully.

Document findings in `logs/` or a QA notebook to maintain traceability between releases.
