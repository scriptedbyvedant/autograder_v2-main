# Educator's Guide to LLM AutoGrader

This guide walks through the workflow supported by the current codebase and highlights best practices for reliable grading sessions.

---

## 1. Purpose & Scope

The platform assists professors with rubric-based grading and feedback generation. You retain full control: all scores and comments can be inspected, edited, and exported before releasing them to students.

---

## 2. Getting Started

### 2.1 Requirements

* An account created via the **Professor Authentication** page (`pages/0_auth.py`).
* A PDF containing the assignment questions, ideal answers, and rubric.
* Student submissions in PDF form or an ILIAS export ZIP.
* A running Ollama service (`ollama serve`) with the model configured in `.env` (default `mistral`).

### 2.2 Logging In

1. Open the application and navigate to the **Professor Authentication** page.
2. Register with your institutional email (domain checks are enforced) if you are a new user.
3. Log in; your profile will appear in the sidebar and Streamlit will remember your session until you sign out or refresh.

---

## 3. Core Workflow

### Phase 1 – Upload Assignment Data

1. Navigate to **Upload Assignment Data for Grading**.
2. Upload the professor PDF. The system extracts questions, ideal answers, and rubric items. Fix structural issues in the source PDF if the parser reports missing sections.
3. Upload student submissions (PDF or ILIAS ZIP). Validation ensures every student has content for each question.
4. When both uploads succeed, click **Start Grading**. Streamlit switches to the grading results page, carrying the parsed data in session state.

> **Tip:** Keep the browser tab open while grading. Refreshing the page clears the temporary session data and you would need to re-upload.

### Phase 2 – Review & Adjust Grades

1. The results page shows a table of scores per student and question. Select a specific student and question from the dropdowns to see details.
2. Review the rubric breakdown. Each criterion has a slider limited to the maximum rubric points.
3. Read or edit the generated feedback in the text area on the right.
4. (Optional) Click **💡 Explanation** to generate a rubric-aligned justification for the current scores.
5. Press **Save changes** to persist your edits. This updates the database and logs the change.

### Phase 3 – Export & Share

* Use the **Download Feedback** section to export a ZIP of individualized PDF reports (generated via ReportLab).
* Share a specific grading result with a colleague by entering their email; they can access it through the **Collaboration Center** page.
* Visit the **Analytics Dashboard** to explore trends across assignments, filter results, or download CSV/PDF reports.

---

## 4. Troubleshooting

| Issue | Resolution |
| --- | --- |
| "Professor PDF missing Q1" error | Confirm each question header uses `Q1`, `Q2`, etc., followed by rubric sections the parser can detect. |
| Student validation failed | Ensure each student answer file contains labelled sections (e.g., `A1:`). Supplying clean PDFs reduces parsing errors. |
| Ollama connection error | Start `ollama serve` and verify `OLLAMA_HOST` in `.env` matches the service URL. |
| Changes not saving | Confirm you clicked **Save changes** after adjusting sliders or feedback. Refreshing the page without saving discards edits. |
| Empty analytics charts | Ensure grading results exist for the selected filters; otherwise reset filters to `All`. |

---

## 5. Frequently Asked Questions

**Can I rerun grading after editing the rubric?**
> Yes. Re-upload the updated professor PDF and student submissions, then start a new grading run. Previous results remain stored in the database under their original assignment identifiers.

**Does manual feedback influence future grading?**
> Not yet. Corrections are stored for auditing but the retrieval store is not updated automatically in this version. Future releases will incorporate corrections into the vector store and fine-tuning workflow.

**Is there an in-app fine-tuning assistant?**
> No. Earlier documentation referenced a `pages/3_fine_tuning.py` helper, but it is not part of this repository snapshot. Fine-tuning currently requires a manual pipeline outside the app.

---

## 6. Best Practices

* Use machine-readable PDFs (exported from word processors) to maximize parsing accuracy.
* Keep assignment identifiers (`assignment_no`, `course`, `semester`) consistent; they serve as keys in analytics and sharing features.
* After grading, take a moment to verify a few exported PDFs to ensure formatting meets your expectations.
* Record major grading decisions or rubric tweaks in `logs/` for future reference or to share with collaborators.

---

## 7. Future Enhancements (Roadmap)

The following educator-facing features are planned but not yet implemented:

* Automatic incorporation of manual corrections into retrieval context.
* Streamlit-based fine-tuning assistant with guided Colab notebook.
* Student-facing portal for viewing released grades.
* Support for additional modalities (images, tables) beyond the current text-centric workflow.

Community contributions are welcome—see the main README for guidelines.
