# Project Report: LLM AutoGrader – Current Capabilities & Next Steps

---

## 1. Executive Summary

The LLM AutoGrader project delivers a Streamlit-based workflow that automates rubric-aligned grading with Large Language Models served through Ollama. Professors upload assignment rubrics and student submissions, review model-generated feedback, and make human-in-the-loop adjustments before exporting or sharing results. This document summarises the features implemented in the current repository snapshot and identifies areas that remain aspirational or in progress.

---

## 2. Delivered Functionality

### 2.1 Upload & Normalisation

* Professor PDFs and student submissions (PDF or ILIAS ZIP) are parsed with PyMuPDF and regex utilities.
* The upload page validates that every student has content for each rubric question before grading proceeds.
* Parsed artifacts remain in Streamlit session state, avoiding premature persistence.

### 2.2 Grading Engine

* `grade_block` orchestrates routing across text, math, and code graders.
* Text grading uses structured prompts, a LangChain output schema, and duplicate model calls to improve stability.
* The code grader executes Python via subprocess, awarding rubric points based on unit tests or safe fallbacks when tests are absent.
* A lightweight retrieval store (Sentence Transformers or TF-IDF fallback) provides contextual exemplars when available.

### 2.3 Human Oversight

* Professors adjust rubric sliders and feedback text in the results page and persist changes with one click.
* Corrections are recorded in `grading_corrections`, preserving the original model output for auditability.
* Individual results can be shared with colleagues, who access them through the collaboration centre.

### 2.4 Analytics & Reporting

* The dashboard renders student summaries, question performance, and calendar heatmaps using pandas and Plotly.
* Filtered datasets can be exported to CSV, and auto-generated PDF summaries capture headline insights.
* Feedback exports produce ZIP archives of per-student PDF reports.

---

## 3. Technical Foundations

| Layer | Notes |
| --- | --- |
| Frontend | Multi-page Streamlit application with session-scoped state management. |
| Models | Ollama-hosted LLM (default `mistral`) with optional fallback heuristics for math and code. |
| Retrieval | In-memory `MultimodalVectorStore` seeded during upload; no persistent FAISS index yet. |
| Persistence | PostgreSQL tables `grading_results`, `grading_corrections`, and `result_shares`, plus authentication tables for professors. |
| Testing | `pytest` harness covering parsing utilities and schema validation; golden dataset approach recommended for richer coverage. |

---

## 4. Limitations & Deferred Work

The repository contains references to features that are not part of the current implementation. Key gaps include:

* **Multi-agent consensus:** Grading presently executes duplicate sequential runs rather than true parallel personas with consensus logic.
* **Persistent RAG updates:** Manual corrections do not update the retrieval store; embeddings are session-bound.
* **Fine-tuning assistant:** Earlier designs mentioned a Streamlit page and `training/` directory for LoRA fine-tuning. These assets are absent here and require external workflows.
* **Database ingestion tables:** Uploaded professor/student data lives exclusively in memory. Database schemas for `prof_data` and `student_data` have not been built.
* **Evaluation tooling:** Advanced metrics that rely on DeepEval, SciPy, or similar packages are optional; they are not included in `requirements.txt`.

Recognising these gaps keeps expectations aligned with the code and clarifies priorities for future development.

---

## 5. Roadmap Highlights

1. **Session Persistence Enhancements** – Store parsed professor and student data in PostgreSQL (or another durable store) to survive browser refreshes.
2. **Dynamic Retrieval Updates** – Append human corrections to the vector store and expose provenance in the UI.
3. **True Multi-Agent Grading** – Introduce parallel personas with a configurable consensus strategy and richer disagreement analytics.
4. **Fine-Tuning Workflow** – Reintroduce the Streamlit assistant, Colab notebook, and `training/` artefacts for LoRA adapter management.
5. **Extended Modalities** – Expand parsing and grading to cover structured tables, diagrams, and multimedia responses.
6. **Comprehensive Evaluation Suite** – Integrate semantic evaluation frameworks and statistical tests once dependencies are agreed upon.

---

## 6. Contribution Guidelines (Summary)

* Align new features with the architecture described in `project_docs/ARCHITECTURE.md`.
* Document any dependency additions or schema changes in the README.
* Extend automated tests when modifying parsing, grading logic, or persistence.
* Update this report and other project docs when significant features graduate from roadmap to implementation.

---

## 7. Conclusion

LLM AutoGrader currently delivers a practical end-to-end grading assistant while leaving space for meaningful enhancements. By consolidating the implemented behaviour in this report, contributors and stakeholders can distinguish between the core product and aspirational features, ensuring roadmap discussions start from an accurate baseline.
