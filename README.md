# LLM AutoGrader

LLM AutoGrader is a Streamlit-based teaching assistant that automates grading workflows with large language models. It ingests professor rubrics and student submissions (text, code, images, PDFs), runs rubric-aligned grading with explainable feedback, and exposes collaborative dashboards for educators.

## Table of Contents
- [Overview](#overview)
- [Key Capabilities](#key-capabilities)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Database Configuration](#database-configuration)
  - [External Services](#external-services)
- [Running the Application](#running-the-application)
- [Typical Workflow](#typical-workflow)
- [Utilities](#utilities)
- [Testing and Quality](#testing-and-quality)
- [Troubleshooting](#troubleshooting)
- [Further Documentation](#further-documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview
The platform combines a multi-page Streamlit interface, a PostgreSQL persistence layer, and a modular grading engine that orchestrates text, code, and multimodal evaluators. It supports human-in-the-loop corrections, multi-agent consensus, retrieval-augmented grading, and analytics that let instructors track cohort performance over time.

## Key Capabilities
- **Rubric-driven LLM grading** with explainable feedback in English, German, and Spanish.
- **Multimodal ingestion** for PDFs, scanned responses, and structured uploads from LMS exports (ILIAS-ready ZIPs).
- **Multi-agent consensus** graders that compare perspectives before confirming a score.
- **Retrieval-augmented evaluation** via a sentence-transformer or TF-IDF vector store for exemplar lookups.
- **Human oversight** workflows: edit grades, share results, and audit corrections.
- **Analytics dashboard** for filtering by course, semester, language, or student.

## Architecture at a Glance
1. **Streamlit Frontend (`app.py`, `pages/`)** – Authentication, PDF/ILIAS upload, grading review, collaboration center, dashboards, and profile management.
2. **Grading Engine (`grader_engine/`)** – Routes requests to specialized graders (text, code, math, multimodal) with fallback-safe RAG and explainability modules.
3. **Data Layer (`database/`)** – Lightweight connection pooling, schema bootstrap, and helper methods for sharing and correction history.
4. **Integrations (`ilias_utils/`, `pdf_utils/`)** – Parsing LMS archives, generating feedback ZIPs, and documentation for rollout.
5. **Ops (`mlops/`, `logs/`, `tests/`)** – Hooks for MLflow tracking and automated schema/grade validation.

## Repository Layout
```
.
├── app.py
├── pages/
│   ├── 0_auth.py            # Professor login and registration
│   ├── 1_upload_data.py     # PDF/ILIAS ingestion, rubric parsing, vector store seeding
│   ├── 2_grading_result.py  # Review, approve, download LMS-ready ZIPs, and share grading output
│   ├── 3_collaboration_center.py
│   ├── 3_dashboard.py       # Performance analytics
├── grader_engine/
│   ├── text_grader.py       # Rubric-aligned text grading with Ollama + adapters
│   ├── multimodal_grader.py # Calls Ollama REST endpoint for multimodal prompts
│   ├── multi_agent.py       # Consensus orchestrator
│   └── ...
├── ilias_utils/             # LMS bridges, feedback ZIP generator (Download Feedback)
├── database/
│   ├── postgres_handler.py  # Connection pool and CRUD helpers
│   └── db_connection.py     # YAML-driven connection helper
├── utils/                   # Shared helpers
├── tests/
│   └── test_grading_validation.py
├── schema.sql               # Baseline grading tables
├── requirements.txt
├── project_docs/            # Architecture, data flow, evaluation, and educator guides
└── validate_zip.py          # CLI validation for LMS ZIP uploads
```

## Prerequisites
- Python 3.9 or newer
- pip (or pipx)
- PostgreSQL 13+ with a database accessible to the app
- [Ollama](https://ollama.ai/download) 0.5+ for running local LLMs (e.g., `mistral`)
- Build tools for native dependencies (libpq for psycopg2, mupdf for PyMuPDF)
- (Optional) Docker, if you prefer to run PostgreSQL in a container

## Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-org>/autograder.git
   cd autograder
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   > Tip: `PyMuPDF`, `psycopg2-binary`, and `torch` may take a few minutes to compile or download.

## Configuration
### Environment Variables
Create a `.env` file in the project root (loaded by `dotenv` in the grading engine):
```ini
# .env
# Ollama inference
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral

# Embeddings for the RAG store
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Optional LangChain settings
LANGCHAIN_TRACING_V2=false
LANGCHAIN_ENDPOINT=
LANGCHAIN_API_KEY=
```
Adjust values to match the model you intend to serve with Ollama.

### Database Configuration
Two modules reference the database:
- `pages/0_auth.py` uses direct connection credentials for registration and login.
- `database/postgres_handler.py` provides pooled access for grading data, sharing, and analytics.

By default both expect:
```
host=localhost
port=5432
database=autograder_db
user=vedant
password=vedant
```
Update these to match your environment. You can either:
- Create matching credentials in PostgreSQL, **or**
- Edit the defaults directly, **or**
- Instantiate `PostgresHandler(conn_params=...)` wherever it is used (recommended for production).

1. **Create PostgreSQL role and database** (example using Dockerized Postgres):
   ```bash
   docker run --name autograder-postgres -e POSTGRES_USER=vedant \
     -e POSTGRES_PASSWORD=vedant -e POSTGRES_DB=autograder_db \
     -p 5432:5432 -d postgres:16
   ```

2. **Apply the schema**
   ```bash
   psql postgresql://vedant:vedant@localhost:5432/autograder_db -f schema.sql
   ```

3. **Create auxiliary tables expected by the UI**
   ```sql
   CREATE TABLE IF NOT EXISTS professors (
       id SERIAL PRIMARY KEY,
       university_email VARCHAR(255) UNIQUE NOT NULL,
       username VARCHAR(100) UNIQUE NOT NULL,
       password_hash TEXT NOT NULL,
       subjects TEXT,
       sessions TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE IF NOT EXISTS result_shares (
       id SERIAL PRIMARY KEY,
       owner_professor_email VARCHAR(255) NOT NULL,
       shared_with_email VARCHAR(255) NOT NULL,
       grading_result_id INTEGER REFERENCES grading_results(id) ON DELETE CASCADE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

4. **Optional YAML configuration** – If you prefer not to hardcode credentials, create `credentials.yaml` in the project root so that `database/db_connection.py` can retrieve the same details:
   ```yaml
   host: localhost
   port: 5432
   database: autograder_db
   user: autograder
   password: change-me
   ```

### External Services
1. **Ollama**
   ```bash
   # Install (macOS/Linux). See https://ollama.ai/download for Windows.
   curl -fsSL https://ollama.ai/install.sh | sh

   # Start the Ollama daemon
   ollama serve

   # Pull the model configured in your .env (example: mistral)
   ollama pull mistral
   ```

2. **Sentence-transformer cache (optional)** – The first run of `sentence-transformers` downloads model weights to `~/.cache`. Ensure the runtime user has write permissions.

## Running the Application
1. Activate your virtual environment if not already active: `source .venv/bin/activate`.
2. Ensure PostgreSQL and Ollama are running (per the configuration above).
3. Launch Streamlit from the project root:
   ```bash
   streamlit run app.py
   ```
4. Open the provided URL (default `http://localhost:8501`). Streamlit will hot-reload when you modify source files.

## Typical Workflow
1. **Authenticate** – Register with a university email and sign in from `pages/0_auth.py`.
2. **Upload materials** – Provide professor rubric PDFs and student submissions in `Upload Assignment PDFs`.
3. **Review parsed content** – Validate extracted questions, ideal answers, and rubrics before grading.
4. **Trigger grading** – Run automated grading; multi-agent evaluators call the Ollama endpoint under the hood.
5. **Inspect results** – Use the grading result page to review rubric-level scores, override feedback, and share outcomes.
6. **Analyze performance** – Filter cohorts in the dashboard for trends across semesters, courses, or languages.
7. **Collaborate** – Share specific grading records with colleagues through the collaboration center.

## Utilities
- `validate_zip.py` – CLI to validate ILIAS ZIP exports before ingesting them.
- `rag_utils.py` – Helper functions to seed and query the multimodal vector store.
- `mlops/` – Stubs for wiring MLflow tracking of grading runs.
- `logs/` – Default location for application logs if you choose to persist them.

## Testing and Quality
Automated tests live under `tests/`.
```bash
pytest
```
`tests/test_grading_validation.py` asserts grading schema integrity and score consistency. Extend this suite as you add graders or schema changes.

## Troubleshooting
- **`psycopg2` build errors** – Install PostgreSQL client libraries (`sudo apt install libpq-dev` on Debian/Ubuntu, `brew install postgresql` on macOS).
- **`Could not connect to Ollama`** – Ensure `ollama serve` is running and that `OLLAMA_HOST` matches the service URL.
- **`PyMuPDF` import errors** – Confirm Python >= 3.9 and reinstall with `pip install --force-reinstall PyMuPDF`.
- **Empty grading results** – Check that embeddings downloaded successfully (the first run may take a minute) and that your `.env` matches the model pulled by Ollama.
- **Authentication fails** – Verify the `professors` table exists and that the email ends with `@stud.hs-heilbronn.de` (validated in the UI).

## Further Documentation
Extended design notes, data-flow diagrams, evaluation summaries, and educator guidance live in `project_docs/`:
- `ARCHITECTURE.md`
- `DATA_FLOW.md`
- `DESIGN.md`
- `EVALUATION.md`
- `Educator_Guide.md`
- `project_report.md`

## Open Source Credits
LLM AutoGrader is only possible thanks to the maintainers of the following open source projects (grouped by how we use them):

**Framework & UI**
- [Streamlit](https://streamlit.io/) powers the multi-page interface.
- [Plotly](https://plotly.com/python/) renders interactive dashboards.

**Machine Learning & LLM Ops**
- [PyTorch](https://pytorch.org/) underpins model execution.
- [Hugging Face Transformers](https://huggingface.co/docs/transformers) supplies pretrained LLMs.
- [Sentence-Transformers](https://www.sbert.net/) generates text embeddings.
- [LangChain](https://www.langchain.com/), [langchain-community](https://github.com/langchain-ai/langchain), and [langchain-ollama](https://github.com/langchain-ai/langchain-ollama) orchestrate prompt flows.
- [Ollama](https://ollama.ai/) serves local LLM endpoints.
- [peft](https://github.com/huggingface/peft), [bitsandbytes](https://github.com/TimDettmers/bitsandbytes), [accelerate](https://github.com/huggingface/accelerate), and [trl](https://github.com/huggingface/trl) handle efficient fine-tuning.

**Data Processing & Utilities**
- [pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), and [sympy](https://www.sympy.org/en/index.html) provide core scientific tooling.
- [python-dotenv](https://saurabh-kumar.com/python-dotenv/), [regex](https://pypi.org/project/regex/), and Python's standard library power configuration and parsing.
- [Pillow](https://python-pillow.org/), [PyMuPDF](https://pymupdf.readthedocs.io/), and [ReportLab](https://www.reportlab.com/dev/opensource/) support PDF and image handling.


**Retrieval, Storage & Auth**
- [scikit-learn](https://scikit-learn.org/) provides TF–IDF fallbacks.
- [psycopg2](https://www.psycopg.org/) integrates with [PostgreSQL](https://www.postgresql.org/).
- [bcrypt](https://github.com/pyca/bcrypt) secures password storage.
- [Docker](https://www.docker.com/), [MLflow](https://mlflow.org/), and vector store backends such as [FAISS](https://github.com/facebookresearch/faiss) and [Chroma](https://www.trychroma.com/) are supported out of the box as optional integrations.

Please honour the individual licenses referenced above (and the full list in `requirements.txt`) when redistributing this project.
## Contributing
Contributions are welcome. Please open an issue describing the change you propose, fork the repository, create a feature branch, and submit a pull request with tests where applicable.

## License
This project is distributed under the terms of the [GNU General Public License v3.0](LICENSE). By contributing or redistributing, you agree to comply with the obligations of GPLv3, including making source code for derivative works available under the same license and preserving copyright notices.
