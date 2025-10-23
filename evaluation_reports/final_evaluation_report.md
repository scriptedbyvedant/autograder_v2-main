# Rapid Evaluation Summary – LLM AutoGrader (Mock Data)

> **Disclaimer:** The following results are synthesized for presentation purposes. They illustrate how the evaluation report will look once real benchmark data is collected.

---

## 1. Assessment Accuracy

| Assessment Type | Lecturer Agreement | Notes |
| --- | --- | --- |
| Text Responses | **91%** | Based on rubric-aligned prompts and RAG context. |
| Code Assignments | **88%** | Partial credit awarded even without full test suites. |
| Mathematical Problems | **86%** | Symbolic comparison occasionally penalised for equivalent forms. |
| Multimodal Responses | **83%** | OCR quality and parsing noise reduce agreement slightly. |

![Accuracy Comparison](figure_accuracy.png)

**Interpretation:** Across mock evaluations, the system stayed within 9–17 percentage points of lecturer scores. Multimodal questions remain the most challenging and will benefit from additional OCR normalisation.

---

## 2. Turnaround Time

![Turnaround Time](figure_turnaround.png)

The simulated pilot shows grading turnaround dropping from the manual baseline of ~96 hours to under 40 hours by week eight. Even with mock data, the trend illustrates the potential time savings once lecturers fully adopt the workflow.

---

## 3. Feature Usage Snapshot

![Usage Share](figure_usage.png)

| Feature | Usage Share |
| --- | --- |
| Grading Results Page | 42% |
| Analytics Dashboard | 28% |
| Explanation Tool | 18% |
| Collaboration Centre | 12% |

Lecturers spend most time in the grading results page, with analytics gaining traction as cohorts grow. Collaboration is still emerging; future training sessions can emphasise peer review workflows.

---

## 4. Observations & Next Steps

1. **Data Quality:** Prepare a real golden dataset so future reports contain measured accuracy instead of mock values.
2. **RAG Feedback Loop:** Incorporate lecturer corrections into the retrieval store to lift multimodal and math agreement.
3. **Dashboard Regression Tests:** Automate CSV exports and chart validation to protect analytics quality.
4. **Cloud Pilot:** Validate turnaround improvements on the proposed GCP architecture (Cloud Run, Cloud Functions, Cloud SQL).

---

## 5. Attachments

- `figure_accuracy.png`
- `figure_turnaround.png`
- `figure_usage.png`

These figures are generated placeholders included in `evaluation_reports/` and can be replaced with real evaluations once available.
