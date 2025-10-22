
# Comprehensive Evaluation Strategy

This document outlines the detailed, module-by-module evaluation plan for the Automated Grading Framework. For each component, it analyzes the available evaluation options and provides a clear justification for the chosen, open-source method.

---

### 1. Data Ingestion & ETL Module (`1_upload_data.py`)

*   **What We Need to Evaluate:** The accuracy of the `PyMuPDF` and regular expression-based parser in correctly extracting and structuring the **questions, rubric, and student answers** from various PDF files.

*   **Available Options:**
    1.  **Manual Spot-Checking:**
        *   *Advantages:* Simple to perform, requires no setup, fast for a very small number of documents.
        *   *Disadvantages:* Not scalable, highly subjective, not statistically valid, and likely to miss subtle but critical edge-case errors (e.g., incorrect parsing of a specific rubric format).
    2.  **Error Rate Monitoring:**
        *   *Advantages:* Easy to implement by wrapping the parsing logic in a try-except block; effectively catches 100% of catastrophic failures where the program would otherwise crash.
        *   *Disadvantages:* Provides a false sense of security. It cannot detect logical errors, such as misattributing an answer to the wrong question or failing to extract the last item in a rubric. The parser can "succeed" but still produce garbage data.
    3.  **Golden Dataset Testing:**
        *   *Advantages:* Provides objective, quantifiable, and reproducible metrics (e.g., F1-score, Precision). An automated script compares the parser's output against a "perfect" ground truth, catching both catastrophic and subtle logical errors. It enables regression testing to ensure future changes don't break existing functionality.
        *   *Disadvantages:* Requires a significant upfront investment of time to create a diverse and representative "golden dataset" of PDFs and their corresponding ideal JSON outputs.

*   **Chosen Method: Golden Dataset Testing**
    *   **Open-Source Confirmation:** This is a methodology, and its implementation will exclusively use open-source tools, primarily **`pytest`** for the testing framework and Python's standard libraries for file handling and comparison.
    *   **Justification:** The quality of the data entering the system is non-negotiable. While it requires upfront effort, the Golden Dataset method is the only one that provides true, quantifiable confidence in the parser's accuracy. It moves from "it seems to work" to "it is 99.2% accurate on these 15 document types." This rigor is essential for a reliable application and justifies the initial time investment.

---

## Core Grader Evaluations

### 2.1. Evaluation of the Multi-Agent Text Grader

*   **What We Need to Evaluate:**
    1.  **Numeric Score Accuracy:** Comparison of the AI's score to a human expert's score.
    2.  **Feedback Quality:** The relevance, helpfulness, and factual correctness of the generated text.
    3.  **Consensus Reliability (RQ1):** The statistical consistency among the different AI agents.

*   **Available Options for Feedback Quality:**
    1.  **Lexical Similarity Metrics (e.g., BLEU, ROUGE):**
        *   *Advantages:* Simple to calculate, fast, and completely objective.
        *   *Disadvantages:* Fundamentally unsuited for this task. They only measure n-gram overlap with a reference answer, not semantic meaning, factual accuracy, or logical reasoning. They cannot determine if feedback is helpful or even correct.
    2.  **LLM-as-a-Judge (Proprietary):**
        *   *Advantages:* Highly scalable and capable of evaluating complex, abstract qualities of the text.
        *   *Disadvantages:* Often relies on closed-source, proprietary models (e.g., GPT-4), which violates our open-source constraint. It can be expensive, and the "judge" model may have its own biases.
    3.  **DeepEval (Open-Source Framework):**
        *   *Advantages:* It is **open-source**, specifically designed for evaluating LLM outputs, and provides metrics for the exact problems we face, such as `Faithfulness` (fact-checking against a context) and `AnswerRelevancy`. It integrates cleanly with `pytest` for automated testing.
        *   *Disadvantages:* Requires some configuration and a clear understanding of what each metric is measuring to be used effectively.

*   **Chosen Method: A Hybrid of DeepEval and Open-Source Statistical Libraries**
    *   **Open-Source Confirmation:** This approach exclusively uses open-source libraries: **`DeepEval`** for feedback quality, **`SciPy`** and **`NumPy`** for numeric score analysis (MAE, Pearson's r), and **`simpledorff`** for Krippendorff's Alpha.
    *   **Justification:** No single tool can evaluate this complex system. A hybrid approach is necessary.
        *   **For Feedback Quality, `DeepEval` is chosen** because it is the only open-source option that can look beyond word-matching to assess the *semantic quality* of the generated text, which is paramount.
        *   **For Numeric Accuracy, standard statistical methods are chosen** because they are the universally accepted standard for comparing a model's score to a human baseline.
        *   **For Consensus Reliability, Krippendorff's Alpha is chosen** because it is the most robust academic standard for measuring inter-rater reliability, accounting for chance agreement in a way that simpler metrics (like variance) do not.

### 2.2. Evaluation of the Code Grader

*   **What We Need to Evaluate:**
    1.  **Execution Accuracy:** The accuracy of the unit test execution within the Docker sandbox.
    2.  **Feedback Quality:** The pedagogical value of the LLM-generated feedback on code style and correctness.

*   **Available Options for Feedback Quality:**
    1.  **LLM-as-a-Judge:**
        *   *Advantages:* Scalable.
        *   *Disadvantages:* Not open-source, and a generic LLM lacks the specific pedagogical context to know what constitutes "good" feedback for a student learning to code.
    2.  **Qualitative Human Review by Experts:**
        *   *Advantages:* The undisputed "gold standard" for assessing pedagogical value. Human instructors can spot nuances, assess tone, and determine if the feedback would actually help a student learn—qualities that an AI judge cannot.
        *   *Disadvantages:* It is subjective, time-consuming, and does not scale.

*   **Chosen Method: Execution Accuracy & Qualitative Human Review**
    *   **Open-Source Confirmation:** The objective part uses open-source tools (`Docker`, `pytest`). The subjective part is a methodology, not a tool, and is by nature open and transparent.
    *   **Justification:** This module's dual nature requires a dual evaluation.
        *   **For the Objective Score:** A simple **Execution Accuracy Percentage** is perfect. It's a binary, clear, and unimpeachable metric derived from comparing the sandbox's `unittest` results to the ground truth.
        *   **For the Subjective Feedback:** **Qualitative Human Review is chosen** over an LLM-as-a-Judge because scalability is less important than authenticity. To gain user trust, the feedback must be genuinely helpful, and only human experts can be the judge of that. For this specific task, human insight is more valuable than automated metrics.

### 2.3. Evaluation of the Math Grader

*   **What We Need to Evaluate:**
    1.  **Symbolic Correctness:** The accuracy of the symbolic math engine (e.g., SymPy) in correctly evaluating the student's mathematical expressions.
    2.  **Feedback Quality:** The clarity and pedagogical value of the LLM-generated feedback explaining *why* a mathematical answer is correct or incorrect.

*   **Available Options:**
    1.  **Manual Calculation:** Manually solve the problems and compare the results. This is slow and prone to human error.
    2.  **Automated Symbolic Comparison:** Use a symbolic math library to programmatically compare the student's final expression against a known "golden" solution. This is fast, deterministic, and highly accurate.
    3.  **LLM-as-a-Judge for Feedback:** Use a powerful LLM to evaluate the quality of the generated feedback.

*   **Chosen Method: Automated Symbolic Comparison & DeepEval**
    *   **Open-Source Confirmation:** We will use **`SymPy`** for the symbolic comparison and **`DeepEval`** for feedback analysis, both of which are open-source.
    *   **Justification:** This hybrid approach addresses both facets of the math grader.
        *   **For Symbolic Correctness:** **`SymPy` is chosen** because it allows for a definitive, automated, and mathematically sound way to check for the equivalence of symbolic expressions. This provides an objective, unimpeachable score for correctness.
        *   **For Feedback Quality:** **`DeepEval` is chosen** to ensure the textual explanation is factually grounded in the mathematical error and is relevant to the student's mistake, preventing generic or unhelpful feedback.

### 2.4. Evaluation of the Multimodal Grader

*   **What We Need to Evaluate:**
    1.  **Visual Interpretation Accuracy:** The model's ability to correctly interpret the content of images, charts, and diagrams.
    2.  **Integrated Reasoning:** The model's capacity to combine information from both text and images to accurately assess the student's answer against the rubric.
    3.  **Feedback Quality:** The quality of the feedback, ensuring it references both textual and visual elements where appropriate.

*   **Available Options:**
    1.  **Ad-hoc Manual Review:** Simply looking at the output and subjectively deciding if it's correct. This is not rigorous or reproducible.
    2.  **Proprietary Multimodal Evaluation Models:** Use closed-source, powerful multimodal models as judges. This violates the open-source constraint and can be expensive.
    3.  **Human Evaluation with a Structured Rubric:** Have human experts evaluate the multimodal output against a specific, structured rubric that asks questions like, "Did the model correctly identify the key elements in the diagram?" and "Does the feedback correctly reference the visual information?"

*   **Chosen Method: Human Evaluation with a Structured Rubric**
    *   **Open-Source Confirmation:** This is a methodology, not a specific tool, and is by nature open and transparent.
    *   **Justification:** The automated evaluation of multimodal reasoning is a complex, cutting-edge research problem. For the practical purposes of this application, **a structured human review is the only truly reliable method**. It is the "gold standard" for assessing nuanced understanding that combines different data types. While not scalable, it provides the most accurate and actionable feedback on the performance of the multimodal grader.

---

## Supporting AI System Evaluations

### 3.1. Evaluation of the RAG Integration Module

*   **What We Need to Evaluate:** The relevance and completeness of the documents retrieved from the FAISS vector store.

*   **Available Options:**
    1.  **End-to-End Evaluation:**
        *   *Advantages:* Requires no extra tools or setup.
        *   *Disadvantages:* It's an indirect and unreliable signal. A good final grade could have occurred *despite* bad retrieval, and vice-versa. It doesn't provide actionable insight into the RAG pipeline itself.
    2.  **Ragas (Open-Source Framework):**
        *   *Advantages:* It is **open-source** and the purpose-built tool for this exact problem. It isolates the retrieval step and provides clear, actionable metrics like `context_precision` and `context_recall`.
        *   *Disadvantages:* Requires the creation of a curated evaluation dataset containing queries and their expected retrieved documents.

*   **Chosen Method: Ragas Framework**
    *   **Open-Source Confirmation:** **`Ragas`** is a well-known, Apache 2.0 licensed open-source project.
    *   **Justification:** Using a specialized tool is vastly superior to indirect measurement. **Ragas is chosen** because it allows us to diagnose the health of our RAG pipeline directly. Knowing our `context_precision` is low, for example, tells us we need to improve our chunking or embedding strategy. This level of targeted insight is impossible with an end-to-end approach.

### 3.2. Evaluation of the Explainability Module (`explainer.py`)

*   **What We Need to Evaluate:** The clarity, accuracy, and pedagogical value of the generated explanation, ensuring it correctly justifies the score by explicitly referencing the rubric and the student's answer.

*   **Available Options:**
    1.  **Human Review (Likert Scale):**
        *   *Advantages:* Provides a direct measure of user satisfaction and perceived clarity.
        *   *Disadvantages:* Subjective, slow, and doesn't scale well.
    2.  **DeepEval Framework:**
        *   *Advantages:* **Open-source** and allows for the creation of precise, automated, and objective metrics. We can move beyond a simple rating to get a specific score for specific qualities.
        *   *Disadvantages:* Requires some initial setup for custom metrics.

*   **Chosen Method: DeepEval Framework with Custom Metrics**
    *   **Open-Source Confirmation:** **`DeepEval`** is an open-source framework.
    *   **Justification:** **DeepEval is chosen** because it allows us to create a highly specific and automated metric that perfectly matches our goal. We will create a custom **"Rubric Coverage"** metric. This metric programmatically parses the rubric and checks if the generated explanation explicitly addresses every single criterion. This provides a direct, objective score for the explanation's completeness, which is far more valuable and reliable than a subjective human rating.

---

## System-Wide Process Evaluation

### 4.1. Evaluation of the Fine-Tuning Pipeline

*   **What We Need to Evaluate:** The delta in performance between the base model and the fine-tuned model on a consistent, held-out test set. We need to measure if fine-tuning actually improves grading accuracy and feedback quality.

*   **Available Options:**
    1.  **Training Loss Monitoring:**
        *   *Advantages:* Very easy, as this data is output by the training script by default.
        *   *Disadvantages:* Can be highly misleading. A decreasing loss only proves the model is learning the *training data*. It does not prove the model can *generalize* to new, unseen data, which is the entire point of fine-tuning.
    2.  **Comparative A/B Testing on a Hold-out Set:**
        *   *Advantages:* The scientific standard for measuring impact. It provides clear, quantitative proof of improvement (or lack thereof) by comparing the model's performance before and after fine-tuning on the same unseen data.
        *   *Disadvantages:* Requires the discipline to maintain a strict separation between training data and the held-out test set.

*   **Chosen Method: Comparative A/B Testing on a Hold-out Set**
    *   **Open-Source Confirmation:** This is a methodology that leverages the other open-source tools in our evaluation suite (`DeepEval`, `Ragas`, `pytest`).
    *   **Justification:** This is the only option that can definitively prove the value of the fine-tuning pipeline. **It is chosen** because it directly answers the business question: "Does this feature make our product better?" By running the entire evaluation suite on the base model and then again on the fine-tuned model, we can generate a clear, evidence-based report (e.g., "Fine-tuning improved feedback faithfulness by 15% and reduced scoring error by 10%"), justifying the feature's existence.

---

## 5. Backend Infrastructure Evaluation

### 5.1. Evaluation of Database Technology Choice (PostgreSQL)

*   **What We Need to Evaluate:** The suitability of the chosen database technology (PostgreSQL) against other options, based on the application's specific requirements for data integrity, query complexity, scalability, and ecosystem support.

*   **Available Options:**
    1.  **NoSQL Databases (e.g., MongoDB, Firestore):**
        *   *Advantages:* Flexible schema is good for rapidly changing or unstructured data. Generally easier to scale horizontally.
        *   *Disadvantages:* Weaker transactional guarantees (compared to ACID). Performing complex queries with joins (e.g., getting all student submissions for a specific assignment with rubric details) is difficult and inefficient. The application's data is highly structured and relational, making this a poor fit.
    2.  **SQLite:**
        *   *Advantages:* Extremely simple, serverless, zero-configuration, and stores the entire database in a single file. Excellent for development, testing, or very simple, single-user applications.
        *   *Disadvantages:* Not designed for concurrency. It struggles with multiple users (e.g., several instructors) writing to the database at the same time, which is a key requirement for this web application. It lacks the advanced features and robustness of a full database server.
    3.  **Relational Databases (e.g., PostgreSQL, MySQL):**
        *   *Advantages:* Strong ACID compliance guarantees data integrity and transactional safety, which is critical for academic records. The standardized SQL language is perfect for the complex, relational queries this application needs. Mature, stable, and well-supported technology.
        *   *Disadvantages:* Requires a more rigid schema upfront. Can be more complex to set up and manage than SQLite.

*   **Chosen Method: PostgreSQL (A Relational Database)**
    *   **Open-Source Confirmation:** PostgreSQL is a powerful, well-regarded, and fully open-source object-relational database system with a liberal license.
    *   **Justification:** **PostgreSQL was chosen because the application's data is fundamentally relational and requires high integrity.**
        1.  **Data Integrity is Non-Negotiable:** The system manages grades, student submissions, and feedback. The strong ACID guarantees of PostgreSQL ensure that this critical data is never left in an inconsistent state. A NoSQL database would risk data corruption.
        2.  **Naturally Relational Data:** The data model consists of clear relationships: a `student` has many `submissions`, an `assignment` has many `grades`. A relational database is the most efficient and logical way to model and query these relationships.
        3.  **Requirement for Complex Queries:** The application needs to perform complex joins, aggregations, and reports (e.g., "Find all feedback for this student across all assignments," "Calculate the average score for question 3 on this exam"). SQL is the most powerful and appropriate tool for these tasks.
        4.  **Concurrency and Scalability:** Unlike SQLite, PostgreSQL is designed from the ground up to handle concurrent connections from multiple users, which is essential for a web application used by multiple instructors. It provides a robust foundation that can scale to a large number of users and a large volume of data.

---

## 6. LLM Comparative Evaluation

### 6.1. Evaluation of Different Language Models

*   **What We Need to Evaluate:** The relative performance of different LLMs (e.g., a base model like Llama 3, a fine-tuned version, an API-based model like Gemini) for the specific tasks of grading and feedback generation. The goal is to determine which model provides the best balance of accuracy, quality, cost, and latency for our application.

*   **Available Options:**
    1.  **Public Benchmarks (e.g., MMLU, HumanEval):**
        *   *Advantages:* Standardized scores are readily available for many models, providing a general sense of their capabilities.
        *   *Disadvantages:* These benchmarks are generic and do not measure performance on our highly specific task of rubric-based grading. A model's ability to answer trivia questions (MMLU) is not a good proxy for its ability to provide nuanced, pedagogical feedback based on a rubric.
    2.  **Ad-hoc Manual Testing:**
        *   *Advantages:* Quick and easy to get a "feel" for a model's output on a few examples.
        *   *Disadvantages:* Not reproducible, not scalable, and highly prone to subjective bias. It cannot provide the quantitative data needed for a formal comparison or to justify a decision.
    3.  **Systematic A/B/n Testing on a Hold-out Set:**
        *   *Advantages:* The gold standard for comparative analysis. It provides direct, head-to-head quantitative comparisons of models on the *exact same data* for the *exact same task*. It reuses our entire existing evaluation suite (DeepEval, statistical tests, etc.) to produce a rich, multi-faceted scorecard for each model.
        *   *Disadvantages:* Requires more rigorous setup and execution time than other methods.

*   **Chosen Method: Systematic A/B/n Testing on a Hold-out Set**
    *   **Open-Source Confirmation:** This is a methodology that leverages our entire existing suite of open-source evaluation tools (`DeepEval`, `Ragas`, `SciPy`, `pytest`). No new tools are needed.
    *   **Justification:** **This is the only method that provides actionable, evidence-based results for our specific use case.**
        1.  **Task-Specific Results:** Instead of relying on irrelevant public benchmarks, this method tests the models on the *actual grading tasks* the application performs.
        2.  **Direct, Quantitative Comparison:** The process involves running the entire evaluation suite (from Section 2.1) on a fixed hold-out set, with the only variable being the LLM being called. This produces a clear scorecard comparing each model on metrics like **Mean Absolute Error**, **Feedback Faithfulness**, and **Rubric Coverage**.
        3.  **Evidence-Based Decisions:** This approach allows us to make definitive statements like, "Model X reduces scoring errors by 15% but increases latency by 40% compared to Model Y." This is the critical information needed to make informed decisions about which model to deploy, balancing performance, cost, and user experience. It turns a subjective choice into a data-driven one.
