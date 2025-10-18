# LLM Academic Grading System

This project is an AI-powered multilingual grading platform designed to assist educators in evaluating student submissions. It leverages Large Language Models (LLMs) to provide automated grading, explainability, and rich analytics.

## Features

- **Automated Grading:** Utilizes LLMs to grade student answers based on a provided rubric.
- **Explainability:** Generates explanations for the assigned grades, providing insights into the grading process.
- **Multilingual Support:** Supports grading and feedback in multiple languages.
- **Rich Analytics:** Offers detailed analytics on student performance and grading consistency.

## Getting Started

### Prerequisites

- Python 3.8+
- Pip
- Ollama

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/llm-academic-grading-system.git
   cd llm-academic-grading-system
   ```

2. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the environment variables:**

   Create a `.env` file in the root directory and add the following:

   ```
   OLLAMA_MODEL=mistral
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   DB_TYPE=postgres
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=grading_db
   DB_USER=admin
   DB_PASSWORD=password
   ```

### Running the Application

1. **Start the Ollama service:**

   ```bash
   ollama serve
   ```

2. **Run the Streamlit application:**

   ```bash
   streamlit run main.py
   ```

## Usage

1. **Upload the grading rubric and student submissions.**
2. **The application will automatically grade the submissions and provide feedback.**
3. **Review the grading results and analytics.**

## Contributing

Contributions are welcome! Please open an issue or submit a pull request to contribute to this project.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
