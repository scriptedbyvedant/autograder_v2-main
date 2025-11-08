# Tables Inventory

This README captures every table defined in `thesis.tex` so you can regenerate them externally (spreadsheets, plotting tools, etc.) before embedding into the document.

| Label | Caption (shortened) | Section / Context | Source Data Notes |
| --- | --- | --- | --- |
| `tab:literature_comparison` | Comparison of representative automated grading systems | Chapter 2 – Related Works | Four-row comparison summarising Poličar, Chu, Törnqvist, and DeepEval papers. Data currently inline in LaTeX. |
| `tab:mae_pearson` | Score accuracy vs. human ground truth | Chapter 7 – Results (`Sec.\ accuracy`) | Contains MAE and Pearson’s r for baseline, multi-agent system, and human graders. Values sourced from evaluation notebooks. |
| `tab:tech_stack` | Core technology stack | Appendix A – Implementation Details (`Sec.\ tech_stack`) | Lists component, technology, and rationale columns. Pull data from architecture documentation if regenerating. |
| `tab:grading_results_schema` | Selected `grading_results` fields | Appendix A – Implementation Details (`Sec.\ data_schema`) | Describes schema columns for audit trail. Can be exported from `schema.sql`. |
| `tab:test_environment` | Test environment and tooling | Appendix B – Extended Evaluation Artefacts (`Sec.\ evaluation_environment`) | Summarises hardware/software for experiments; derived from evaluation appendix. |
| `tab:model_comparison` | LLM comparison summary | Appendix B – Extended Evaluation Artefacts (`Sec.\ model_comparison`) | Contains accuracy/latency metrics for Mistral, LLaMA 3, Falcon 7B. Numbers are from synthetic benchmark runs. |

**Workflow Tips**

- When recreating tables, prefer CSV or spreadsheet sources and note the file path here for traceability.
- Keep regenerated assets (e.g., `tab_mae_pearson.csv`, `tab_model_comparison.xlsx`) in this folder or subfolders, and record any updates in this README.
