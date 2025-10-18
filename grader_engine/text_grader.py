# -*- coding: utf-8 -*-
"""
Text grader (compatibility + multimodal-aware normalization)
- Keeps your original fine-tuned / Ollama flow
- Adds support for student_answer_blocks and multimodal_context blocks
- Normalizes rubric across str/dict/list
"""

import os
import json
import re
import difflib
from typing import List, Dict, Any, Optional, Tuple

import torch
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_community.chat_models import ChatOllama
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

load_dotenv()

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

# --- Base Model Configuration ---
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# --- Fine-Tuned Model Configuration ---
BASE_MODEL_NAME = "mistralai/Mistral-7B-v0.1"
ADAPTER_PATH = os.path.join(os.path.dirname(__file__), '..', 'training', 'results', 'final_model')

# -----------------------------------------------------------------------------
# LLM OUTPUT SCHEMA
# -----------------------------------------------------------------------------
response_schemas = [
    ResponseSchema(name="total_score",   description="Sum of rubric points awarded (integer)"),
    ResponseSchema(name="rubric_scores", description="List of objects: {'criteria': string, 'score': integer}"),
    ResponseSchema(name="feedback",      description="Textual feedback aligned with rubric")
]
output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

# -----------------------------------------------------------------------------
# Helpers to handle blocks / strings uniformly
# -----------------------------------------------------------------------------
def _to_blocks(obj: Any) -> List[Dict[str, Any]]:
    """Coerce str|dict|list -> list of {'type':'text','content':...} blocks."""
    if obj is None:
        return []
    if isinstance(obj, list):
        out = []
        for it in obj:
            if isinstance(it, dict):
                if "type" in it and "content" in it:
                    out.append(it)
                elif "content" in it:
                    out.append({"type": it.get("type") or it.get("content_type") or "text", "content": it["content"]})
                else:
                    out.append({"type": "text", "content": json.dumps(it, ensure_ascii=False)})
            elif isinstance(it, str):
                out.append({"type": "text", "content": it})
            else:
                out.append({"type": "text", "content": str(it)})
        return out
    if isinstance(obj, dict):
        if "type" in obj and "content" in obj:
            return [obj]
        return [{"type": obj.get("type") or obj.get("content_type") or "text", "content": obj.get("content", "")}]
    if isinstance(obj, str):
        return [{"type": "text", "content": obj}]
    return [{"type": "text", "content": str(obj)}]

def _blocks_to_text(blocks: Any) -> str:
    return " ".join((b.get("content") or "") for b in _to_blocks(blocks)).strip()

# -----------------------------------------------------------------------------
# PROMPT (UPDATED for Multimodal Context)
# -----------------------------------------------------------------------------
BASE_TEMPLATE = """
You are a strict grader. Grade the student's answer strictly by the provided rubric.
Respond in {language}.

Question:
{question}

Ideal Answer:
{ideal_answer}

Rubric (JSON list of {{'criteria','points'}}):
{rubric_json}

{multimodal_context_block}

Student Answer:
{student_answer}

{exemplar_block}

Instructions:
- For each rubric criterion, assign an INTEGER score between 0 and its 'points' (INCLUSIVE).
- Do NOT invent or add criteria; use EXACTLY the criteria names from the rubric list.
- The 'rubric_scores' array MUST have the SAME length and the SAME criteria (same order is preferred).
- 'total_score' MUST equal the sum of the rubric item scores.
- Provide concise feedback that justifies deductions in {language}.

Respond ONLY with valid JSON matching:
{format_instructions}
"""

def _make_prompt(
    language: str,
    question: str,
    ideal_answer: str,
    rubric_json: str,
    student_answer: str,
    rag_context: Optional[Dict[str, Any]] = None,
    multimodal_context: Optional[str] = None
) -> str:
    """Compose the final prompt; include exemplars and multimodal context if provided."""
    exemplars_txt = ""
    if rag_context:
        ex = rag_context.get("exemplars", []) or []
        if ex:
            snips = []
            for i, item in enumerate(ex[:3], 1):
                txt = str(item.get("text", ""))[:700]
                meta = item.get("meta", {})
                score = meta.get("score", "")
                snips.append(f"Exemplar {i} (score {score}):\n{txt}")
            exemplars_txt = "Context (consistency reference):\n" + "\n\n".join(snips)
        if not ideal_answer and rag_context.get("ideal"):
            ideal_answer = rag_context["ideal"]

    multimodal_context_txt = ""
    if multimodal_context:
        multimodal_context_txt = f"The following context from the professor's materials is also available:\n{multimodal_context}\n"

    tmpl = PromptTemplate(
        template=BASE_TEMPLATE,
        input_variables=[
            "language", "question", "ideal_answer",
            "rubric_json", "student_answer", "exemplar_block",
            "multimodal_context_block"
        ],
        partial_variables={"format_instructions": output_parser.get_format_instructions()},
    )
    return tmpl.format(
        language=language,
        question=question,
        ideal_answer=ideal_answer,
        rubric_json=rubric_json,
        student_answer=student_answer,
        exemplar_block=exemplars_txt,
        multimodal_context_block=multimodal_context_txt
    )

# -----------------------------------------------------------------------------
# ROBUST PARSING + ALIGNMENT HELPERS
# -----------------------------------------------------------------------------
def _extract_json(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return m.group(0) if m else cleaned

def _as_int(x, default: int = 0) -> int:
    try:
        if isinstance(x, (int, float)): return int(round(x))
        if isinstance(x, str): return int(round(float(x.strip())))
    except Exception: pass
    return int(default)

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def _align_and_clamp(
    rubric: List[Dict[str, Any]],
    model_breakdown: List[Dict[str, Any]],
    fuzzy_cutoff: float = 0.60
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    sanity = {"unknown_criteria": [], "over_allocated": [], "coerced_types": False, "model_items_seen": 0}
    if not rubric: return [], sanity

    mm: Dict[str, int] = {}
    keys: List[str] = []
    for it in (model_breakdown or []):
        if not isinstance(it, dict): continue
        c, s_raw = it.get("criteria", ""), it.get("score", 0)
        s = _as_int(s_raw, 0)
        if s != s_raw: sanity["coerced_types"] = True
        k = _normalize(c)
        if k:
            mm[k] = s
            keys.append(k)
            sanity["model_items_seen"] += 1

    aligned: List[Dict[str, Any]] = []
    for r in rubric:
        crit, pts = r.get("criteria", ""), _as_int(r.get("points", 0), 0)
        norm = _normalize(crit)
        if norm in mm:
            sc = mm[norm]
        else:
            match = difflib.get_close_matches(norm, keys, n=1, cutoff=fuzzy_cutoff)
            sc = mm.get(match[0], 0) if match else 0
            if not match: sanity["unknown_criteria"].append(crit)

        if sc > pts: sanity["over_allocated"].append({"criteria": crit, "score": sc, "max": pts})
        sc = max(0, min(sc, pts))
        aligned.append({"criteria": crit, "score": sc})

    return aligned, sanity

def _feedback_header(rubric: List[Dict[str, Any]], aligned: List[Dict[str, Any]], total: int) -> str:
    total_possible = sum(_as_int(r.get("points", 0)) for r in rubric)
    lines = [f"**Total: {int(total)}/{total_possible}**", "Rubric Breakdown:"]
    for r, a in zip(rubric, aligned):
        lines.append(f"- {r.get('criteria','')}: {int(a.get('score',0))}/{_as_int(r.get('points',0))}")
    return "\n".join(lines)

def _get_raw_prediction_finetuned(prompt: str) -> Tuple[str, str]:
    model_id = f"{BASE_MODEL_NAME} (PEFT Adapters)"
    print(f"Loading fine-tuned model from {ADAPTER_PATH}...")
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=False)
    base_model = AutoModelForCausalLM.from_pretrained(BASE_MODEL_NAME, quantization_config=bnb_config, device_map="auto", trust_remote_code=True)
    base_model.config.use_cache = False
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output_sequences = model.generate(input_ids=inputs["input_ids"], max_new_tokens=1024)
    raw_output = tokenizer.decode(output_sequences[0], skip_special_tokens=True)
    return raw_output[len(prompt):].strip(), model_id

def _get_raw_prediction_ollama(prompt: str) -> Tuple[str, str]:
    model_id = OLLAMA_FALLBACK_MODEL
    print(f"Using fallback Ollama model: {model_id}")
    llm = ChatOllama(model=model_id)
    resp = llm.invoke(prompt)
    return resp.content, model_id

# -----------------------------------------------------------------------------
# PUBLIC API (multimodal-aware & backward compatible)
# -----------------------------------------------------------------------------
def grade_answer(
    question: str,
    ideal_answer: str,
    rubric: Any,
    student_answer: Optional[str] = None,
    language: str = "English",
    model_name: Optional[str] = None,
    rag_context: Optional[Dict[str, Any]] = None,
    multimodal_context: Optional[Any] = None,   # may be str or blocks
    return_debug: bool = False,
    include_header_in_feedback: bool = True,
    *,
    # NEW: allow callers to pass blocks directly (compat with multimodal pipeline)
    student_answer_blocks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Grade a single answer, using a fine-tuned or fallback model, now with multimodal context.

    Backward compatible with older code that passed only `student_answer` (str),
    but also accepts `student_answer_blocks` and `multimodal_context` as blocks.
    """
    use_finetuned = os.path.isdir(ADAPTER_PATH)

    # --- Normalize rubric to a list of {'criteria','points'} dicts
    try:
        if isinstance(rubric, str):
            rubric = json.loads(rubric)
    except Exception:
        pass
    if isinstance(rubric, dict) and "criteria" in rubric:
        rubric = rubric.get("criteria", [])
    rubric = rubric or []
    rubric_json = json.dumps(rubric, ensure_ascii=False)

    # --- Normalize student answer to text
    if student_answer_blocks is not None:
        student_answer_text = _blocks_to_text(student_answer_blocks)
    else:
        student_answer_text = (student_answer or "").strip()

    # --- Normalize ideal answer to text
    ideal_answer_text = _blocks_to_text(ideal_answer) if isinstance(ideal_answer, (list, dict)) else (ideal_answer or "")

    # --- Normalize multimodal context to text (if blocks are provided)
    mm_context_text = _blocks_to_text(multimodal_context) if isinstance(multimodal_context, (list, dict)) else (multimodal_context or "")

    prompt_str = _make_prompt(
        language=language,
        question=question,
        ideal_answer=ideal_answer_text,
        rubric_json=rubric_json,
        student_answer=student_answer_text,
        rag_context=rag_context,
        multimodal_context=mm_context_text
    )

    raw, model_id = "", ""
    try:
        if use_finetuned:
            raw, model_id = _get_raw_prediction_finetuned(prompt_str)
        else:
            raw, model_id = _get_raw_prediction_ollama(prompt_str)
    except Exception as e:
        out = {"total_score": 0, "rubric_scores": [{"criteria": r.get("criteria",""), "score": 0} for r in rubric], "feedback": f"Grading failed: {e}"}
        if return_debug:
            out["debug"] = {"model": "N/A", "prompt": prompt_str, "raw_output": str(e), "sanity": {"error": "invoke_failed"}}
        return out

    parsed = {}
    try:
        parsed = output_parser.parse(raw)
    except Exception:
        try:
            parsed = json.loads(_extract_json(raw))
        except Exception:
            parsed = {}

    model_total = _as_int(parsed.get("total_score", 0), 0)
    model_breakdown = parsed.get("rubric_scores", []) or []
    model_feedback = parsed.get("feedback", "")
    if not isinstance(model_feedback, str):
        model_feedback = str(model_feedback)

    aligned, sanity = _align_and_clamp(rubric, model_breakdown)
    total_awarded = int(sum(int(it["score"]) for it in aligned))
    if model_total != total_awarded:
        sanity["model_total"] = model_total
        sanity["recomputed_total"] = total_awarded

    body = model_feedback.strip()
    if include_header_in_feedback:
        header = _feedback_header(rubric, aligned, total_awarded)
        full_feedback = header + ("\n\n" + body if body else "")
    else:
        full_feedback = body

    result = {"total_score": total_awarded, "rubric_scores": aligned, "feedback": full_feedback}
    if return_debug:
        result["debug"] = {"model": model_id, "prompt": prompt_str, "raw_output": raw, "sanity": sanity}
    return result
