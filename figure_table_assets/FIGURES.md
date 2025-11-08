# Figures Inventory

Centralised reference for every figure defined in `thesis.tex`. Use this list to (re)generate the required diagrams manually and keep assets organised outside the LaTeX source.

| Label | Caption (shortened) | Section / Context | Rendering Notes |
| --- | --- | --- | --- |
| `fig:high_level_arch` | Layered system architecture | Chapter 5 – System Architecture, Sec. *High-Level Architectural Overview* | Drawn with TikZ (see lines ~330–370 in `thesis.tex`). Visualises user/app/data layers and arrows between modules. |
| `fig:data_ingestion` | Data ingestion pipeline | Chapter 5 – Data Ingestion and Preprocessing | TikZ swim lanes showing professor vs student ETL stages. Described around lines ~396–436. |
| `fig:core_grading_pipeline` | Core grading pipeline | Chapter 5 – End-to-End Grading Flow | TikZ flow diagram (lines ~440–471) summarising trigger → persistence → UI refresh steps. |
| `fig:agentic_pipeline` | Agentic grading pipeline | Chapter 5 – Multi-Agent Grading Engine | TikZ block diagram (lines ~481–520) combining text and code grading branches. |
| `fig:hitl_pipeline` | Human-in-the-loop correction path | Chapter 5 – HITL Feedback Loop | TikZ sequence-style flow (lines ~534–560) from Streamlit edits to FAISS upsert. |

**How to use this folder**

1. Recreate or export the required diagrams (e.g., from draw.io, Figma, or TikZ compiled outputs).
2. Place rendered assets (PDF/PNG/SVG) alongside this README, mirroring the figure labels in filenames (e.g., `fig_high_level_arch.pdf`).
3. Update the table above with file names and any tooling notes if the generation process changes.
