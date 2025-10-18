
# The Educator's Guide to the Automated Grading Framework

---

## 1. Purpose & Scope

**Goal:** This guide serves as the primary onboarding and reference document for educators using the Automated Grading Framework. Its purpose is to empower you to efficiently and effectively grade student assignments, understand the AI's reasoning, and improve its performance over time.

**Scope:** This document covers the complete user workflow, from uploading assignment materials and grading student submissions to leveraging advanced features like model fine-tuning. It is not intended to be a deep technical reference for developers.

---

## 2. Getting Started

### 2.1. Overview

The Automated Grading Framework is a tool designed to assist you with the grading process. It uses a sophisticated AI Grading Engine to analyze student submissions, provide a score based on your rubric, and generate detailed, constructive feedback. 

Crucially, **you are always in control**. The framework acts as your expert assistant, and you have the final say on every grade. The system is built on a **Human-in-the-Loop** philosophy, meaning your corrections are not only saved but are used to make the AI smarter and more aligned with your standards over time.

### 2.2. Prerequisites

Before you begin, please ensure you have the following:

*   **Professor-level access credentials** to log into the application.
*   **Assignment materials in PDF format.** This includes:
    *   A document containing the assignment questions, the ideal answers, and a detailed grading rubric.
    *   The students' submissions, also in PDF format.

---

## 3. Step-by-Step Walkthrough

This section will guide you through the three main phases of using the application.

### Phase 1: Uploading Your Assignment

First, you need to provide the system with the context for the assignment.

1.  **Navigate** to the **"Upload Data"** page from the main menu.
2.  **Upload the Professor's Document:** Under the "Upload Professor Data" section, upload the PDF that contains your questions, ideal answers, and rubric.
3.  **Upload Student Submissions:** Under the "Upload Student Data" section, upload one or more student answer PDFs.
4.  **Verification:** The system will confirm once the files are successfully parsed and stored.

> #### 📌 **Best Practice: PDF Formatting**
> For the best results, use PDFs where the text is machine-readable (i.e., not a scanned image). This allows the AI to parse the content with the highest accuracy. If you have a very long assignment document, consider splitting it into smaller files for easier processing.

### Phase 2: Grading and Review (The Human-in-the-Loop)

This is where the magic happens. The AI will grade the submissions, and you will review them.

1.  **Navigate** to the **"Grading Result"** page.
2.  **Initiate Grading:** Select the course and assignment you wish to grade and click the **"Start Grading"** button.
3.  **Review the Results:** After a few moments, the results will appear in an interactive table. For each student, you will see:
    *   The question and their answer.
    *   The AI-generated score (`old_score`) and feedback (`old_feedback`).
4.  **Make Corrections:** If you disagree with the AI, simply **click into the table cell** and edit the score or feedback directly. The table works just like a spreadsheet.
5.  **Save Corrections:** When you modify a grade, your correction is saved automatically as `new_score` and `new_feedback`. 

> #### ✨ **How Your Corrections Help**
> Every correction you make is used in two powerful ways:
> 1.  **For Consistency (RAG):** Your correction is immediately stored in the system's "memory" (a Vector Store). When the AI grades the *next* student, it looks at this memory to see how you graded similar answers, helping it stay consistent.
> 2.  **For Long-Term Improvement:** Your corrections become the training data for making the AI model itself better (see Phase 3).

### Phase 3 (Advanced): Improving the AI with the Finetuning Assistant

After you have graded several assignments and made corrections, you can use that data to create a new, smarter version of the AI model that is customized to your specific course and standards.

1.  **Navigate** to the **"Model Finetuning Assistant"** page.
2.  **Step 1: Generate Data:** Click the **"Generate Training Data"** button. The system will package all the corrections you've made into a single `training_dataset.jsonl` file. A download button will appear.
3.  **Step 2: Train in Colab:** 
    *   Follow the link to open Google Colab and set the runtime to `T4 GPU` as instructed.
    *   Copy the provided Python script into a Colab cell.
    *   Upload your `training_dataset.jsonl` file to the Colab environment.
    *   Run the cell. The training will take 15-20 minutes.
4.  **Step 3: Deploy Your Model:**
    *   Once training is complete, a `trained_adapters.npz` file will appear in Colab. Download it.
    *   Move this file into the `training/` folder of this application.
    *   **Restart the application.**

That's it! The application will automatically detect and use your new, fine-tuned model for all future grading tasks.

---

## 4. Troubleshooting & FAQ

*   **Q: The PDF upload failed or the text looks jumbled. Why?**
    *   **A:** This usually happens if the PDF is a scanned image of a document. Please ensure your PDFs are created from a text source (e.g., "Save as PDF" from a word processor). See the Best Practice tip in Phase 1.

*   **Q: The AI's grade seems completely wrong. What should I do?**
    *   **A:** Simply correct it in the results table. The system is designed for this! Your correction provides a valuable data point that helps the AI learn.

*   **Q: How can I trust the AI is being fair and consistent?**
    *   **A:** The system uses two key features for this: the **Multi-Agent System**, where multiple AI agents debate to reach a consensus, and **Retrieval Augmented Generation (RAG)**, which constantly refers to your past corrections to maintain consistency. The final authority, however, is always you.

*   **Q: I deployed a new fine-tuned model but I want to revert to the original. How?**
    *   **A:** Simply delete the `trained_adapters.npz` file from the `training/` directory and restart the application. The system will revert to the base model.

---

## 5. Additional Resources

For users interested in the underlying technical details of the framework, the following documents are available in the project repository:

*   `ARCHITECTURE.md`: A high-level overview of the system components.
*   `DESIGN.md`: A detailed technical design of the software.
*   `DATA_FLOW.md`: A set of diagrams illustrating how data moves through the application.

---

## Next Steps for This Document

As a living document, this guide will evolve with the product. Based on anticipated user feedback, future versions should include:

*   **A section on interpreting the Analytics Dashboard.**
*   **Specific guidance for grading Code Assignments**, including how to write effective `unittest` cases.
*   **A more detailed "Tips and Tricks" section** for writing effective rubrics that the AI can easily understand.
