
# Application Architecture

This document provides a detailed overview of the technical architecture of the automated grading application. It is intended for developers and system administrators.

---

## 1. High-Level Overview

The application is a multi-tiered system composed of a web-based frontend, a robust backend with a relational database, and a sophisticated AI-powered grading engine. 

```mermaid
graph TD
    A[Browser] --> B{Streamlit Frontend};
    B --> C{Backend Server};
    C --> D[PostgreSQL Database];
    C --> E{AI Grading Engine};
    E --> F[LLM APIs / Local Models];
    E --> G[Vector Store];
    C --> H{ILIAS ZIP Parser / FeedbackZipGenerator};
    H --> D;
    B --> H;

    subgraph User Interface
        B
    end

    subgraph Core Logic & Data
        C
        D
        H
    end

    subgraph AI Processing
        E
        F
        G
    end
```

*   **Frontend:** A multi-page Streamlit application provides the user interface for professors and teaching assistants, including dual ingestion paths (PDFs or ILIAS ZIP archives) and a one-click feedback export builder.
*   **Backend:** A Python backend orchestrates the application logic, handling user requests, database interactions, and calls to the grading engine.
*   **Database:** A PostgreSQL database stores all persistent data, including user information, assignment details, student submissions, and grading results.
*   **AI Grading Engine:** A modular engine that leverages Large Language Models (LLMs) to perform the grading. It includes specialized modules for different types of assignments.
*   **Vector Store:** A FAISS-based vector database stores embeddings of past grading decisions to provide historical context (RAG).
*   **LMS Bridges:** ILIAS ingest and feedback export utilities map LMS ZIP archives into per-student records and rebuild graded ZIPs that can be re-uploaded without manual renaming.

---

## 2. Frontend (Streamlit Application)

The frontend is built using Streamlit and is organized into a multi-page application structure.

### **2.1. Directory Structure**

*   `app.py`: The main entry point of the Streamlit application. It handles routing and global configuration.
*   `pages/`: This directory contains the individual pages of the application, such as:
    *   `0_auth.py`: User authentication.
*   `1_upload_data.py`: Interface for professors to upload assignment PDFs, students to submit their work, or staff to ingest an ILIAS archive ZIP via `parse_ilias_zip` (manifests, per-student mapping, and validation preview).
*   `2_grading_result.py`: Displays the results of the grading process.
*   `3_dashboard.py`: Cohort-level analytics, exports, and collaboration aids.
*   `Download Feedback`: A control on the grading page that calls `FeedbackZipGenerator` to package the latest `new_score/new_feedback` into LMS-ready PDFs and a ZIP that matches ILIAS folder/filename conventions.
    *   `3_collaboration_center.py`: Optional workflow for sharing graded artefacts with colleagues.

### **2.2. Authentication and Session Management**

Authentication is managed through the `auth` module. User session data, including login status and user roles, is stored in `st.session_state`. This ensures that sensitive pages are protected and that the application context is maintained as the user navigates between pages.

---

## 3. Backend and Database

The backend logic is tightly integrated with the PostgreSQL database, which serves as the single source of truth.

### **3.1. Database Schema**

The database consists of several key tables:

*   `users`: Stores user credentials and roles (e.g., professor, assistant).
*   `prof_data`: Contains the data uploaded by professors, including the course, assignment number, questions, ideal answers, and grading rubrics.
*   `student_data`: Stores student submissions, linked to a specific assignment.
*   `grading_results`: This is the central table for storing the output of the grading engine. It includes the original student answer, the AI-generated score and feedback (`old_feedback`), and any human-in-the-loop corrections (`new_feedback`, `new_score`).

### **3.2. Data Handler (`database/postgres_handler.py`)**

All database interactions are abstracted away by the `PostgresHandler` class. This class provides a standardized interface for executing queries (SELECT, INSERT, UPDATE) and managing connections. This centralized approach ensures consistency and simplifies database management.

---

## 4. The AI Grading Engine (`grader_engine/`)

This is the core of the application where the AI-powered grading takes place. 

```mermaid
graph TD
    A[Request from Backend] --> B{Router};
    B --> |Text| C[Text Grader];
    B --> |Code| D[Code Grader];
    B --> |Multi-Agent| E[Multi-Agent Grader];
    B --> |Multimodal| F[Multimodal Grader];

    C --> G{RAG Integration};
    E --> G;
    
    G --> H[Vector Store];
    C --> I{Explainability Module};
    E --> I;

    I --> J[Final Grade & Feedback];
```

### **4.1. Router (`router.py`)**

The `Router` is the main entry point for the grading engine. It inspects the assignment type (e.g., text, code, multimodal) and directs the request to the appropriate specialized grader.

### **4.2. Multi-Agent Grader (`multi_agent.py`)**

To improve reliability and reduce bias, the system employs a multi-agent consensus mechanism:

1.  **Agent Roles:** Multiple LLM agents are instantiated with slightly different personas (e.g., a "strict" grader, a "lenient" grader, a "by-the-book" grader).
2.  **Concurrent Grading:** These agents grade the same submission in parallel using `concurrent.futures`.
3.  **Consensus:** The scores and feedback from each agent are collected. The final score is typically the mean or median of the agents' scores, and the variance is used as a confidence metric.
4.  **Final Review:** A final "meta-agent" reviews the collected feedback and synthesizes it into a single, high-quality explanation.

### **4.3. Code Grader (`code_grader.py`)**

The code grader provides a secure and comprehensive way to evaluate programming assignments:

1.  **Sandboxed Execution:** Student code is executed within a secure, isolated Docker container to prevent any potential security risks.
2.  **Unit Testing:** The code is run against a set of predefined `unittest` cases. The results (pass/fail) form the basis of the objective score.
3.  **Qualitative Feedback:** An LLM analyzes the student's code, along with the unit test results, to provide qualitative feedback on code style, efficiency, best practices, and potential areas for improvement.

### **4.4. RAG Integration (`rag_integration.py`)**

To ensure consistency over time, the grading engine uses Retrieval Augmented Generation (RAG):

1.  **Vector Store:** When a human-in-the-loop correction is made, the grading context (question, student answer, corrected feedback) is embedded and stored in a FAISS vector store.
2.  **Contextual Retrieval:** When grading a new submission, the engine queries the vector store to find the most similar previously graded examples.
3.  **Prompt Injection:** These historical examples are injected into the LLM prompt, providing valuable context that helps the model "remember" how similar cases were graded in the past.

### **4.5. Explainability Module (`explainer.py`)**

This module is responsible for generating the detailed, rubric-aligned justifications for the final score. It takes the grading results and structures them into a clear, easy-to-understand format that explains which criteria were met and why.

---

## 5. Model Management (Future Work)

The current release focuses on deterministic prompts, retrieval grounding, and manual human-in-the-loop corrections. Automated fine-tuning workflows, adapter management, and associated tooling (e.g., Colab scripts or additional Streamlit pages) are explicitly out of scope and will be revisited when institutional requirements call for managed MLOps support.
