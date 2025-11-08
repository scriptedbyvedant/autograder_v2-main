# Figures Inventory

Centralised reference for every figure defined in `thesis.tex`. Use this list to (re)generate the required diagrams manually and keep assets organised outside the LaTeX source.

| Label | Caption (shortened) | Section / Context | Rendering Notes |
| --- | --- | --- | --- |
| `fig:high_level_arch` | Layered system architecture | Chapter 5 – System Architecture, Sec. *High-Level Architectural Overview* | Drawn with TikZ (see lines ~330–370 in `thesis.tex`). Visualises user/app/data layers and arrows between modules. Raw LaTeX copied to `FIGURES.tex`. |
| `fig:data_ingestion` | Data ingestion pipeline | Chapter 5 – Data Ingestion and Preprocessing | TikZ swim lanes showing professor vs student ETL stages. Described around lines ~396–436. Source in `FIGURES.tex`. |
| `fig:core_grading_pipeline` | Core grading pipeline | Chapter 5 – End-to-End Grading Flow | TikZ flow diagram (lines ~440–471) summarising trigger → persistence → UI refresh steps. Source in `FIGURES.tex`. |
| `fig:agentic_pipeline` | Agentic grading pipeline | Chapter 5 – Multi-Agent Grading Engine | TikZ block diagram (lines ~481–520) combining text and code grading branches. Source in `FIGURES.tex`. |
| `fig:hitl_pipeline` | Human-in-the-loop correction path | Chapter 5 – HITL Feedback Loop | TikZ sequence-style flow (lines ~534–560) from Streamlit edits to FAISS upsert. Source in `FIGURES.tex`. |

**How to use this folder**

1. Recreate or export the required diagrams (e.g., from draw.io, Figma, or TikZ compiled outputs).
2. Place rendered assets (PDF/PNG/SVG) alongside this README, mirroring the figure labels in filenames (e.g., `fig_high_level_arch.pdf`).
3. Update the table above with file names and any tooling notes if the generation process changes.
4. The file `FIGURES.tex` contains the exact LaTeX environments copied from `thesis.tex` for reference or reuse.

## LaTeX Sources

```latex
% Extracted from thesis.tex (around line 1)
\begin{figure}[htbp]
  \centering
  \begin{adjustbox}{center,max width=\textwidth}
  \begin{tikzpicture}[
    every node/.style={font=\small},
    module/.style={draw, rounded corners, thick, fill=white, align=center, minimum width=3.1cm, minimum height=1.0cm},
    highlight/.style={fill=gray!10},
    arrow/.style={-{Latex[length=3mm,width=2mm]}, thick},
    node distance=2.4cm
  ]
    \node[module, highlight] (browser) {User's Browser\\\footnotesize HTTPS/TLS};
    \node[module, highlight, right=2.8cm of browser] (ui) {Streamlit\\Web UI};
    \node[draw, rounded corners, thick, fit=(browser)(ui), inner sep=10pt, label=above:{User Layer}, fill=blue!5] (userlayer) {};

    \node[module, highlight, right=3.2cm of ui] (backend) {Backend Logic\\\footnotesize Python services};
    \node[module, highlight, above=1.6cm of backend] (engine) {AI Grading Engine\\\footnotesize Orchestrator};
    \node[module, highlight, below=1.6cm of backend] (db) {PostgreSQL\\\footnotesize ACID datastore};
    \node[draw, rounded corners, thick, fit=(backend)(engine)(db), inner sep=10pt, label=above:{Application Layer}, fill=green!5] (applayer) {};

    \node[module, highlight, right=3.2cm of engine] (llm) {LLMs\\\footnotesize Local/API};
    \node[module, highlight, below=1.6cm of llm] (faiss) {FAISS\\\footnotesize Vector Store};
    \node[module, highlight, below=1.6cm of faiss] (docker) {Secure Docker\\\footnotesize Sandbox};
    \node[draw, rounded corners, thick, fit=(llm)(faiss)(docker), inner sep=10pt, label=above:{AI \& Data Layer}, fill=orange!10] (ailayer) {};

    \draw[arrow] (browser) -- node[above, font=\scriptsize]{streamlit session} (ui);
    \draw[arrow] (ui) -- node[above, font=\scriptsize]{function calls} (backend);
    \draw[arrow] (backend) -- node[right, font=\scriptsize]{grading jobs} (engine);
    \draw[arrow] (backend) -- node[right, font=\scriptsize]{SQL queries} (db);
    \draw[arrow] (engine) -- node[above, font=\scriptsize]{prompts/results} (llm);
    \draw[arrow] (engine) -- node[right, font=\scriptsize]{embeddings} (faiss);
    \draw[arrow] (engine) -- node[right, font=\scriptsize]{code exec} (docker);
  \end{tikzpicture}
  \end{adjustbox}
\caption{Layered system architecture. Educators interact through a hardened Streamlit UI (user layer), the Python application layer validates inputs and coordinates persistence, and the AI \& data layer hosts inference, retrieval memory, and the secure execution sandbox required for code grading.}
\label{fig:high_level_arch}
\end{figure}


% Extracted from thesis.tex (around line 2)
\begin{figure}[htbp]
  \centering
  \begin{adjustbox}{center,max width=\textwidth}
  \begin{tikzpicture}[
    scale=1.15,
    transform shape,
    every node/.style={font=\small},
    node distance=1.1cm,
    flowstep/.style={draw, rounded corners, thick, fill=white, align=center, minimum width=4.0cm, minimum height=0.9cm},
    arrow/.style={-{Latex[length=3mm,width=2mm]}, thick}
  ]
    \node[flowstep] (prof1) {Professor uploads assignment PDF};
    \node[flowstep, below=of prof1] (prof2) {Streamlit forwards file to backend};
    \node[flowstep, below=of prof2] (prof3) {Parser extracts text and structure};
    \node[flowstep, below=of prof3] (prof4) {Structured data stored in \texttt{prof\_data}};
    \node[draw, dashed, rounded corners, thick, fit=(prof1)(prof4), inner sep=8pt, label=above:{Professor Workflow}] (profbox) {};

    \node[flowstep, right=6cm of prof1] (stu1) {Student uploads submission PDF};
    \node[flowstep, below=of stu1] (stu2) {Backend extracts submission text};
    \node[flowstep, below=of stu2] (stu3) {Submission stored in \texttt{student\_data}};
    \node[draw, dashed, rounded corners, thick, fit=(stu1)(stu3), inner sep=8pt, label=above:{Student Workflow}] (stubox) {};

    \draw[arrow] (prof1) -- (prof2);
    \draw[arrow] (prof2) -- (prof3);
    \draw[arrow] (prof3) -- (prof4);
    \draw[arrow] (stu1) -- (stu2);
    \draw[arrow] (stu2) -- (stu3);

    \draw[arrow] (prof3.east) to[out=0,in=180] node[above, font=\scriptsize, yshift=4pt]{Shared parser and Postgres handler} (stu2.west);
  \end{tikzpicture}
  \end{adjustbox}
\caption{Data ingestion pipeline. The left swim lane captures the instructor flow from PDF upload to structured rubric storage, while the right lane shows how student submissions are parsed and stored alongside their metadata via the shared parser and Postgres handler.}
\label{fig:data_ingestion}
\end{figure}


% Extracted from thesis.tex (around line 3)
\begin{figure}[htbp]
  \centering
  \begin{adjustbox}{center,max width=\textwidth}
  \begin{tikzpicture}[
    scale=1.1,
    transform shape,
    every node/.style={font=\small},
    node distance=2.3cm,
    flowstep/.style={draw, rounded corners, thick, fill=white, align=center, minimum width=3.4cm, minimum height=1.0cm},
    arrow/.style={-{Latex[length=3mm,width=2mm]}, thick}
  ]
    \node[flowstep] (start) {Professor triggers grading};
    \node[flowstep, right=of start] (fetch) {Backend gathers rubric and submissions};
    \node[flowstep, right=of fetch] (engine) {AI grading engine};
    \node[flowstep, right=of engine] (agentic) {Agentic consensus and RAG};
    \node[flowstep, right=of agentic] (persist) {Persist result in \texttt{grading\_results}};
    \node[flowstep, right=of persist] (ui) {Streamlit UI refresh for review};

    \draw[arrow] (start) -- (fetch) -- (engine) -- (agentic) -- (persist) -- (ui);
  \end{tikzpicture}
  \end{adjustbox}
\caption{Core grading pipeline from grading trigger to UI refresh. Each step emphasises the responsibility handoff: the backend gathers inputs, the grading engine executes consensus logic, results are written to \texttt{grading\_results}, and the Streamlit dashboard reflects the new state for instructor review.}
\label{fig:core_grading_pipeline}
\end{figure}


% Extracted from thesis.tex (around line 4)
\begin{figure}[htbp]
  \centering
  \begin{adjustbox}{center,max width=\textwidth}
  \begin{tikzpicture}[
    scale=1.1,
    transform shape,
    every node/.style={font=\small},
    node distance=2.4cm and 1.6cm,
    flowstep/.style={draw, rounded corners, thick, fill=white, align=center, minimum width=3.5cm, minimum height=1.0cm},
    arrow/.style={-{Latex[length=3mm,width=2mm]}, thick}
  ]
    \node[flowstep] (router) {Assignment router};
    \node[flowstep, right=3cm of router] (text) {Text assignments\\Multi-agent grader};
    \node[flowstep, below=2.4cm of text] (code) {Code assignments\\Secure code grader};

    \draw[arrow] (router) -- (text);
    \draw[arrow] (router) -- (code);

    \node[flowstep, right=2.8cm of text] (rag) {Retrieve rubric-aligned context};
    \node[flowstep, right=2.8cm of rag] (agents) {Parallel LLM agents};
    \node[flowstep, right=2.8cm of agents] (aggregate) {Aggregate scores\\and confidence};
    \node[flowstep, right=2.8cm of aggregate] (meta) {Meta-agent synthesises feedback};

    \draw[arrow] (text) -- (rag) -- (agents) -- (aggregate) -- (meta);

    \node[flowstep, right=2.8cm of code] (dockerprep) {Prepare Docker sandbox + tests};
    \node[flowstep, right=2.8cm of dockerprep] (execution) {Execute unit tests};
    \node[flowstep, right=2.8cm of execution] (codereview) {LLM code review};
    \node[flowstep, right=2.8cm of codereview] (coderesult) {Final code grade};

    \draw[arrow] (code) -- (dockerprep) -- (execution) -- (codereview) -- (coderesult);

    \node[flowstep, right=3cm of meta] (output) {Return final score, feedback, confidence};
    \draw[arrow] (meta) -- (output);
    \draw[arrow] (coderesult) to[out=25,in=215] (output);
  \end{tikzpicture}
  \end{adjustbox}
  \caption{Agentic grading pipeline. The upper path details the retrieval-augmented, multi-agent consensus flow for textual submissions, while the lower path captures the Docker-backed execution and LLM review used for programming assignments; both converge to a unified score, confidence interval, and narrative feedback.}
  \label{fig:agentic_pipeline}
\end{figure}


% Extracted from thesis.tex (around line 5)
\begin{figure}[htbp]
  \centering
  \begin{adjustbox}{center,max width=\textwidth}
  \begin{tikzpicture}[
    scale=1.1,
    transform shape,
    every node/.style={font=\small},
    node distance=2.6cm,
    flowstep/.style={draw, rounded corners, thick, fill=white, align=center, minimum width=3.7cm, minimum height=1.0cm},
    arrow/.style={-{Latex[length=3mm,width=2mm]}, thick}
  ]
    \node[flowstep] (edit) {Educator edits score or feedback};
    \node[flowstep, right=of edit] (ui) {Streamlit data editor submits row};
    \node[flowstep, right=of ui] (backend) {Backend validates and prepares update};
    \node[flowstep, right=of backend] (update) {Persist changes in \texttt{grading\_results}};
    \node[flowstep, right=of update] (embed) {Embed corrected example};
    \node[flowstep, right=of embed] (faiss) {Upsert vector into FAISS index};
    \node[flowstep, right=of faiss] (toast) {Confirmation toast \& enriched RAG memory};

    \draw[arrow] (edit) -- (ui) -- (backend) -- (update) -- (embed) -- (faiss) -- (toast);
  \end{tikzpicture}
  \end{adjustbox}
\caption{Human-in-the-loop correction path. Instructor edits are validated, persisted, embedded, and pushed into the FAISS index, ensuring subsequent grading runs can retrieve human-vetted exemplars and that the UI confirms the update.}
\label{fig:hitl_pipeline}
\end{figure}
```
