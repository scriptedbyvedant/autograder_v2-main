# grader_engine/explainer.py
"""
Explanation generation module for AI-based grading framework.
Provides a multilingual explanation interface for assigned scores,
justifying rubric criteria met/missed and offering improvement suggestions.
"""
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_community.chat_models import ChatOllama

load_dotenv()

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

response_schemas = [
    ResponseSchema(name="explanation", description="Detailed, synchronized explanation text"),
]
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

EXPLAINER_TEMPLATE = """
You are an expert teaching assistant. Provide a clear, synchronized explanation in {language} for why the student received the assigned score.

Question:
{question}

Ideal Answer:
{ideal_answer}

Rubric Criteria (with possible points):
{rubric_list}

Student Answer:
{student_answer}

Assigned Score: {assigned_score}

Instructions:
- Refer to each rubric criterion and state whether it was satisfied or missed.
- Justify why points were awarded or deducted in alignment with the rubric.
- Suggest concrete improvements for the student's answer.
- Ensure the breakdown of scores matches the rubric exactly.

Respond ONLY with JSON matching the following schema:
{format_instructions}
""".strip()

EXPLAIN_PROMPT = PromptTemplate(
    template=EXPLAINER_TEMPLATE,
    input_variables=["language", "question", "ideal_answer", "rubric_list", "student_answer", "assigned_score"],
    partial_variables={"format_instructions": output_parser.get_format_instructions()}
)

def generate_explanation(
    question: str,
    ideal_answer: str,
    rubric: List[Dict[str, Any]],
    student_answer: str,
    assigned_score: float,
    language: str = "English",
    model_name: Optional[str] = None,
    return_debug: bool = False
):
    """
    Returns:
        - explanation string (if return_debug=False)
        - (explanation string, debug dict) if return_debug=True, where debug = {model, prompt, raw_output}
    """
    model_id = model_name or DEFAULT_MODEL

    rubric_list = "\n".join(f"- {item.get('criteria','')} ({int(item.get('points', 0))} pts)" for item in rubric)

    prompt_str = EXPLAIN_PROMPT.format(
        language=language,
        question=question,
        ideal_answer=ideal_answer,
        rubric_list=rubric_list,
        student_answer=student_answer,
        assigned_score=str(assigned_score)
    )

    llm = ChatOllama(model=model_id)
    try:
        resp = llm.invoke(prompt_str)
        raw = resp.content
    except Exception as e:
        if return_debug:
            return f"Explanation failed: {e}", {"model": model_id, "prompt": prompt_str, "raw_output": f"{e}"}
        return f"Explanation failed: {e}"

    # Parse
    try:
        parsed = output_parser.parse(raw)
        explanation = parsed.get('explanation', '') if isinstance(parsed, dict) else ''
    except Exception:
        explanation = raw.strip()

    if return_debug:
        return explanation, {"model": model_id, "prompt": prompt_str, "raw_output": raw}
    return explanation
