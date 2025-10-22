# Technical Design Notes

This document captures the current design of the LLM AutoGrader repository. It focuses on how data is modeled, how grading executes, and where human-in-the-loop corrections fit in.

---

## 1. Architectural Intent

* Keep the user experience entirely inside Streamlit.
* Store instructor rubrics and student answers in `st.session_state` during a grading session.
* Persist only finalized grading outputs, corrections, and sharing metadata to PostgreSQL.
* Use Ollama-hosted models (default `mistral`) for text grading while providing light-weight math and code graders.
* Allow professors to inspect and adjust results immediately, then export feedback packages or share items.

---

## 2. Data Model & Persistence

Only three tables are required for the current functionality (plus `professors`, provisioned alongside authentication scripts):

| Table | Purpose | Key Columns |
| --- | --- | --- |
| `grading_results` | Stores first-run scores and feedback for each student/question pair. | `student_id`, `professor_id`, `assignment_no`, `question`, `language`, `old_score`, `new_score`, serialized `student_answer`. |
| `grading_corrections` | Audit log capturing every manual override. | `grading_result_id` (via workflow), `old_score`, `new_score`, `old_feedback`, `new_feedback`, `editor_id`, `created_at`. |
| `result_shares` | Grants read access to colleagues. | `owner_professor_email`, `shared_with_email`, `grading_result_id`, `created_at`. |

`database/postgres_handler.py` owns the schema bootstrap, connection pooling, and CRUD helpers (`fetch_results`, `share_result`, `update_grading_result_with_correction`, etc.). There are no tables for professor uploads or student submissions; session state fills that role.

---

## 3. Streamlit Session Structure

`st.session_state` keys created during upload/grading:

* `prof_data` – Normalized professor metadata and rubric (`questions`, `ideal_answer` blocks, etc.).
* `students_data` – Nested dictionary of student IDs mapping to per-question content blocks.
* `multimodal_vs` – Optional `MultimodalVectorStore` for retrieval-augmented grading.
* `grading_cache` – Dict containing the signature of the last grading run and per-question results, enabling UI edits without re-running models.
* `logged_in_prof` – Authentication context used across pages.

---

## 4. Grading Workflow

1. `pages/2_grading_result.py` iterates over `(student, question)` pairs and calls `grader_engine.multi_agent.grade_block`.
2. `grade_block` performs simple heuristics to classify the question as `text`, `code`, or `math`.
3. For text, it loads RAG exemplars, calls `text_grader.grade_answer` twice, and averages the totals.
4. For code, `code_grader.grade_code` executes Python via a subprocess and awards rubric points based on test pass rates (or fallbacks if no tests are provided).
5. For math, `math_grader` compares expressions and returns rubric-aligned scores.
6. `fuse` (in `multi_agent.py`) aggregates duplicate runs into a final score and flags high disagreement.
7. Results are serialized, persisted to PostgreSQL, and cached in session for subsequent edits.

### 4.1 Text Grader Highlights

* Prompt template includes question, ideal answer, rubric JSON, optional RAG exemplars, and instructions to return JSON.
* `StructuredOutputParser` enforces the response schema.
* Duplicate model calls mitigate occasional non-determinism; both runs use the same prompt data.
* Rubric normalization utilities coerce strings/dicts/lists into a consistent list of `{criteria, points}`.

### 4.2 Code Grader Highlights

* Uses the host Python interpreter with `subprocess.run` inside a temporary directory.
* Awards points proportionally to tests passed; if no tests, syntax and smoke-run heuristics award partial credit.
* Returns `(total_points_awarded, per_criterion_breakdown, details)` for downstream fusion.

### 4.3 Retrieval Module

* `MultimodalVectorStore` attempts to load Sentence Transformers (`all-MiniLM-L6-v2`).
* Falls back to TF-IDF cosine similarity or a no-op backend if embeddings cannot be built.
* Items are keyed by question ID and encompass question text, ideal answers, and rubric JSON serialized from the professor PDF.
* Corrections do not currently mutate the store; it is session-scoped.

---

## 5. Human-in-the-Loop Editing

* Rubric scores are controlled by sliders; total points are recomputed client-side.
* Feedback is edited within a `st.text_area`.
* Pressing **Save changes** writes the new values to `grading_results`, logs the old/new pair in `grading_corrections`, and updates the cached session copy.
* Explanation button triggers `grader_engine.explainer.generate_explanation` on demand, using current rubric scores and answer text.

---

## 6. Collaboration & Analytics

* Collaboration center exposes helper functions from `PostgresHandler` to list owned and shared results.
* Dashboard pulls combined datasets (`fetch_my_results`, `fetch_shared_with_me`), applies filters, and renders Plotly figures. Optional downloads are produced with pandas (`to_csv`) and ReportLab (PDF summary).

---

## 7. Authentication Snapshot

* `pages/0_auth.py` connects directly to PostgreSQL using connection parameters defined inline.
* Professors use bcrypt-hashed passwords; domain enforcement ensures institutional addresses.
* After a successful login, relevant profile fields are stored in session for personalized dashboards and sharing features.

---

## 8. Roadmap Considerations

The repository currently omits the following capabilities that may appear in older documentation:

* Database-backed storage of parsed professor/student uploads.
* Full multi-agent orchestration with parallel personas and consensus strategies.
* Automatic retrieval-store refresh after manual corrections.
* Streamlit fine-tuning assistant, Colab integration script, and `training/` directory.
* Evaluation tooling that depends on external libraries (DeepEval, SciPy, simpledorff). Adding them would require updating `requirements.txt`.

These features remain candidates for future releases; contributors should treat the notes above as authoritative for the present codebase.
