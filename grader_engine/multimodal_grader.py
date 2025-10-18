
# File: grader_engine/multimodal_grader.py
# NOTE: This file has been modified to use a local, text-only open-source model (e.g., Mistral via Ollama)
# instead of a multimodal cloud API. The "multimodal" name is kept for interface compatibility.

import os
import json
import re
from typing import List, Dict, Any
import requests # Using requests to call the local Ollama API

from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# --- OLLAMA CONFIGURATION ---
# Assumes Ollama is running locally.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_ENDPOINT = f"{OLLAMA_HOST}/api/generate"

# ----------------------------------------------------------------------------
# LLM OUTPUT SCHEMA
# ----------------------------------------------------------------------------
response_schemas = [
    ResponseSchema(name="total_score",   description="Sum of rubric points awarded (integer)"),
    ResponseSchema(name="rubric_scores", description="List of objects: {'criteria': string, 'score': integer}"),
    ResponseSchema(name="feedback",      description="Textual feedback aligned with rubric")
]
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# ----------------------------------------------------------------------------
# PROMPT
# ----------------------------------------------------------------------------
PROMPT_TEXT = '''
You are a strict grader. Grade the student's answer strictly by the provided rubric.
The student's answer and the professor's materials are provided as text.
Respond in {language}.

**Question:**
{question}

**Ideal Answer:**
{ideal_answer}

**Rubric (JSON list of {{'criteria','points'}}):**
{rubric_json}

**Instructions:**
- For each rubric criterion, assign an INTEGER score between 0 and its 'points' (INCLUSIVE).
- Do NOT invent or add criteria; use EXACTLY the criteria names from the rubric list.
- The 'rubric_scores' array MUST have the SAME length and the SAME criteria.
- 'total_score' MUST equal the sum of the rubric item scores.
- Provide concise feedback that justifies deductions in {language}.

Respond ONLY with valid JSON matching:
{format_instructions}
'''

# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def _extract_json(raw: str) -> str:
    # Ollama with format='json' often returns a clean JSON string, but we keep this for robustness.
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r'\{.*\}', cleaned, re.DOTALL)
    return m.group(0) if m else cleaned

def _as_int(x, default: int = 0) -> int:
    try:
        if isinstance(x, (int, float)): return int(round(x))
        if isinstance(x, str): return int(round(float(x.strip())))
    except (ValueError, TypeError): pass
    return int(default)

# ----------------------------------------------------------------------------
# PUBLIC API
# ----------------------------------------------------------------------------
def grade_answer_multimodal(
    question: str,
    ideal_answer: str,
    rubric: List[Dict[str, Any]],
    student_answer_blocks: List[Dict[str, Any]],
    multimodal_context: List[Dict[str, Any]],
    language: str = "English",
    return_debug: bool = False
) -> Dict[str, Any]:
    '''
    Grade a single answer using a local, open-source LLM (e.g., Mistral via Ollama).
    NOTE: This is a text-only implementation. It will ignore images.
    '''
    rubric = json.loads(rubric) if isinstance(rubric, str) else (rubric or [])
    rubric_json = json.dumps(rubric, ensure_ascii=False)

    # --- Construct the text-only prompt ---
    # Filter for and join text content from all sources.
    prof_context_text = "\n".join([item['content'] for item in (multimodal_context or []) if item.get('content_type') == 'text'])
    student_answer_text = "\n".join([item['content'] for item in (student_answer_blocks or []) if item.get('type') == 'text'])

    final_prompt = PROMPT_TEXT.format(
        language=language,
        question=question,
        ideal_answer=ideal_answer,
        rubric_json=rubric_json,
        format_instructions=output_parser.get_format_instructions()
    )
    # Add the context and student answer to the prompt
    full_prompt_with_data = f"{final_prompt}\n\n--- PROFESSOR'S CONTEXT MATERIALS ---\n{prof_context_text}\n\n--- STUDENT'S ANSWER ---\n{student_answer_text}"


    # --- Call the local Ollama model ---
    raw_output = ""
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt_with_data,
            "stream": False,
            "format": "json" # Request JSON output from Ollama
        }
        response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        # The actual JSON string is in the 'response' key
        raw_output = response.json().get("response", "")
        
    except (requests.RequestException, json.JSONDecodeError) as e:
        error_message = f"Grading failed: Could not connect to Ollama at {OLLAMA_ENDPOINT}. Is it running? Error: {e}"
        out = {"total_score": 0, "rubric_scores": [{"criteria": r.get("criteria", ""), "score": 0} for r in rubric], "feedback": error_message}
        if return_debug:
            out["debug"] = {"model": OLLAMA_MODEL, "prompt": full_prompt_with_data, "raw_output": str(e)}
        return out

    # --- Parse the response ---
    parsed = {}
    try:
        # Ollama with format='json' should return valid JSON, but we parse it safely.
        parsed = json.loads(_extract_json(raw_output))
    except (json.JSONDecodeError, TypeError):
        # Fallback if the output is not clean JSON
        parsed = {}

    # Basic alignment and clamping
    aligned_scores = []
    model_breakdown = parsed.get("rubric_scores", []) or []
    for i, r_item in enumerate(rubric):
        score = 0
        if i < len(model_breakdown) and isinstance(model_breakdown[i], dict):
            raw_score = model_breakdown[i].get('score', 0)
            score = _as_int(raw_score, 0)
        max_points = _as_int(r_item.get("points", 0), 0)
        score = max(0, min(score, max_points))
        aligned_scores.append({"criteria": r_item.get("criteria", ""), "score": score})

    total_awarded = sum(item["score"] for item in aligned_scores)
    
    result = {
        "total_score": parsed.get("total_score", total_awarded),
        "rubric_scores": aligned_scores,
        "feedback": parsed.get("feedback", "")
    }
    if return_debug:
        result["debug"] = {"model": OLLAMA_MODEL, "prompt": full_prompt_with_data, "raw_output": raw_output}
        
    return result
