
# Detailed Data Flow Diagrams

This document provides a series of detailed diagrams illustrating the data flow through every major pipeline in the Automated Grading Framework. 

---

## 1. Data Ingestion Pipeline (ETL)

This pipeline describes how course materials (from professors) and student submissions are processed from raw PDFs or ILIAS LMS archives into structured, queryable data in the PostgreSQL database.

```mermaid
sequenceDiagram
    participant Prof as Professor
    participant Stu as Student
    participant UI as Streamlit UI (st.file_uploader)
    participant Parser as PDF/ILIAS Parser (PyMuPDF / regex / parse_ilias_zip)
    participant Backend as Backend Logic (1_upload_data.py)
    participant DB as PostgresHandler
    participant PG as PostgreSQL

    rect rgb(224,255,255)
        Prof->>UI: Upload professor PDF (questions, rubric) OR ILIAS ZIP export
        UI->>Backend: Pass file bytes
        Backend->>Parser: Extract text / unpack ZIP
        Parser-->>Backend: Return raw text + manifest
        Backend->>Parser: Parse into structured data
        Parser-->>Backend: Return JSON structure
        Backend->>DB: execute_query INSERT into prof_data
        DB->>PG: SQL insert
    end

    rect rgb(255,250,205)
        Stu->>UI: Upload submission PDF
        UI->>Backend: Pass file bytes
        Backend->>Parser: Extract text
        Parser-->>Backend: Return raw text
        Backend->>DB: execute_query INSERT into student_data
        DB->>PG: SQL insert
    end
```

**Description:**

The ingestion process happens in two distinct (but similar) workflows:

*   **Professor Workflow:** 
    1. The professor uploads a PDF containing the assignment details.
    2. The backend uses `PyMuPDF` to extract text and regular expressions (`re`) to parse it into a structured format (questions, rubric, etc.).
    3. The structured data is saved to the `prof_data` table in the PostgreSQL database.

*   **Student Workflow:**
    1. The student uploads their submission as a PDF.
    2. The backend uses `PyMuPDF` to extract the raw text of their answer.
    3. This text is saved to the `student_data` table, linked to the appropriate assignment.

*   **ILIAS Workflow (Professor and Students combined):**
    1. An instructor uploads a full ILIAS ZIP export containing assignment context and student submissions.
    2. `parse_ilias_zip` unpacks the archive, normalises filenames, maps each submission to a student ID, and surfaces a manifest/coverage preview in the UI.
    3. Parsed questions/criteria flow into `prof_data`, and per-student files are stored in `student_data`, ready for grading with no manual renaming.

---

## 2. Core Grading Pipeline

This diagram shows the end-to-end process when a professor initiates a grading job, culminating in the results being displayed on the screen.

```mermaid
graph TD
    A[Start: User clicks Grade] --> B(Backend Logic 2_grading_result.py)
    B --> C[Fetch submissions from student_data]
    B --> D[Fetch rubric from prof_data]
    C --> E[AI Grading Engine]
    D --> E
    E --> F[Agentic Pipeline]
    F --> G(Grading Result score, feedback, confidence)
    G --> H[Insert into grading_results]
    H --> I[Streamlit UI updates]
    I --> J[Professor reviews grades]
```

**Description:**
1.  The process begins when the user starts a grading job from the Streamlit UI.
2.  The backend fetches the relevant student submissions and the corresponding professor-defined rubric from the PostgreSQL database.
3.  This data is dispatched as a job to the **AI Grading Engine**.
4.  The engine performs the complex grading task (detailed in the next section).
5.  The final, aggregated result is returned to the backend.
6.  The backend saves this result to the `grading_results` table for persistence.
7.  The UI is updated to display the new grades in an editable table, completing the flow.

---

## 3. Agentic Grading Engine Pipeline (Deep Dive)

This diagram provides a detailed look inside the AI Grading Engine itself, showing how a single submission is processed by the multi-agent system.

```mermaid
graph TD
    A[Grading Job Received] --> B[Router]
    B --> |text| C[Multi-Agent Grader]
    B --> |code| D[Code Grader]

    subgraph Code Grading Sandbox
        D --> D1[Create Dockerfile + unittests]
        D1 --> D2[docker build & docker run]
        D2 --> D3[Capture unittest stdout]
        D3 --> D4[Parse score]
        D4 --> D5[LLM feedback]
        D5 --> D6[Final code grade]
    end

    subgraph Multi-Agent Text Grading
        C --> C1[RAG retrieval]
        C1 --> C2[Similar past corrections]
        C2 --> C3[Context bundle]

        C --> C4[Concurrent agents]
        C3 --> C4
        C4 --> Agent1[Agent α]
        C4 --> Agent2[Agent β]
        C4 --> AgentN[Agent γ]

        subgraph Single Agent Execution
            Agent1 --> P1[Prompt Builder]
            P1 --> L1[LLM call]
            L1 --> R1[Score + feedback]
        end

        R1 --> C5[Aggregator]
        Agent2 --> C5
        AgentN --> C5

        C5 --> C6[Mean/median + confidence]
        C5 --> C7[Meta-agent synthesis]
        C6 --> C8[Final text grade]
        C7 --> C8
    end

    D6 --> Z[Return Result]
    C8 --> Z
```

**Description:**
*   **Routing:** The engine first routes the job based on the assignment type.
*   **Code Grading:** For code, it enters a secure Docker sandbox to run unit tests for an objective score, then uses an LLM to generate qualitative feedback on the code itself.
*   **Text Grading:** For text, the process is more complex:
    1.  **RAG:** The RAG module first retrieves relevant historical grading examples from the FAISS vector store.
    2.  **Concurrent Grading:** Multiple AI agents, each with a different persona, are spawned in parallel. They each receive the submission, the rubric, and the context from the RAG module.
    3.  **Aggregation:** Once all agents complete, their individual scores are statistically aggregated (e.g., taking the median). The variance in their scores is used as a confidence metric.
    4.  **Synthesis:** A final "meta-agent" reviews the feedback from all other agents and synthesizes it into a single, high-quality, comprehensive piece of feedback for the student.

---

## 4. Human-in-the-Loop (HITL) & RAG Update Pipeline

This pipeline shows what happens when a professor makes a correction to an AI-generated grade. This is a critical feedback loop for the system.

```mermaid
sequenceDiagram
    participant User as Professor
    participant UI as Streamlit UI (`st.data_editor`)
    participant Backend as Backend Logic
    participant DB as PostgresHandler
    participant PG as PostgreSQL Database
    participant RAG as RAG Update Module
    participant Embed as Embedding Model
    participant FAISS as FAISS Vector Store

    User->>UI: Edits a score or feedback field in the table
    UI->>Backend: On change, submits the full row of data
    Backend->>DB: Calls `UPDATE grading_results` to set `new_score` and `new_feedback`
    DB->>PG: Executes SQL UPDATE
    PG-->>DB: Confirms update
    DB-->>Backend: Success

    Backend->>RAG: Triggers RAG update with the corrected data
    RAG->>Embed: Creates a document from the question and corrected feedback
    Embed->>RAG: Generates a vector embedding for the document
    RAG->>FAISS: Adds the new vector to the FAISS index
    FAISS-->>RAG: Confirms save
    RAG-->>Backend: Success
    Backend-->>UI: Displays "Correction Saved" toast
```

**Description:**
1.  The professor edits a grade directly in the Streamlit UI.
2.  The backend receives the corrected data.
3.  It first updates the `grading_results` table in the PostgreSQL database, preserving both the original AI grade (`old_feedback`) and the new human-verified grade (`new_feedback`).
4.  Next, this correction is used to improve the RAG system. The corrected feedback is converted into a vector embedding.
5.  This new vector is added to the FAISS vector store, making this human-verified example available for all future grading tasks to improve their context and accuracy.

---




## 5. Feedback Export Pipeline (ILIAS-Compatible ZIP)

This flow shows how reviewed grades are packaged for LMS re-upload.

```mermaid
sequenceDiagram
    participant UI as Streamlit UI (Download Feedback)
    participant Backend as Backend Logic
    participant Export as FeedbackZipGenerator
    participant FS as Temporary Storage

    UI->>Backend: User clicks "Download Feedback"
    Backend->>Export: Fetch latest new_score/new_feedback for assignment
    Export->>FS: Render per-student PDFs + manifest
    Export->>UI: Return ZIP matching ILIAS folder/filename conventions
```

**Description:**
1. From the grading page, the instructor clicks **Download Feedback**.
2. The backend gathers the latest `new_score`/`new_feedback` rows for each student.
3. `FeedbackZipGenerator` renders per-student PDFs and builds a ZIP using the ILIAS naming and folder structure.
4. The UI streams the ZIP so the instructor can upload it back to ILIAS without manual file renaming.
