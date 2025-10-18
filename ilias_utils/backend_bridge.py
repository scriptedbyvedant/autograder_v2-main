# ilias_utils/backend_bridge.py
"""
Bridges ILIAS ingest to your existing graders with ZERO changes
to your PDF code. It:
  - builds grading items (using manifest_adapter),
  - routes each item to graders in grader_engine (if present),
  - returns graded_results grouped per student raw_folder,
  - optional DB persistence stub.
"""
from __future__ import annotations
from typing import Dict, Any, List
import importlib
from pathlib import Path

from .manifest_adapter import build_items_from_ingest


def _safe_import(module_name: str, fallback=None):
    try:
        return importlib.import_module(module_name)
    except Exception:
        return fallback

ge_text = _safe_import("grader_engine.text_grader")
ge_code = _safe_import("grader_engine.code_grader")
ge_explainer = _safe_import("grader_engine.explainer")
ge_multi = _safe_import("grader_engine.multi_agent")
ge_rag = _safe_import("grader_engine.rag_integration")


def _route_item(item: Dict[str, Any]) -> str:
    t = (item.get("type_hint") or "").lower()
    if t in {"free_text", "text"}:
        return "free_text"
    if t in {"code", "programming"}:
        return "code"
    if t in {"numeric", "mixed"}:
        return "numeric"
    if t in {"mcq", "multiple_choice"}:
        return "mcq"

    exts = [Path(a).suffix.lower() for a in item.get("answer_file_arcnames", [])]
    if any(e in {".py", ".java", ".cpp", ".js", ".ts", ".ipynb"} for e in exts):
        return "code"
    if any(e in {".pdf", ".docx", ".txt", ".md"} for e in exts):
        return "free_text"
    return "free_text"


def _grade_free_text(item: Dict[str, Any]) -> Dict[str, Any]:
    question_id = item["question_id"]
    rubric = item.get("rubric_items", [])
    if ge_text and hasattr(ge_text, "grade_answer"):
        return ge_text.grade_answer(
            question=question_id,
            rubric=rubric,
            answer_text=item.get("answer_text") or "",
            context=item.get("resources", {})
        )
    return {
        "question_id": question_id,
        "type": "free_text",
        "rubric_scores": [{"criteria": r["criteria"], "score": 0, "max_score": r["max_score"]} for r in rubric],
        "total_score": 0,
        "feedback": "Placeholder: free-text grader not wired."
    }


def _grade_code(item: Dict[str, Any]) -> Dict[str, Any]:
    question_id = item["question_id"]
    rubric = item.get("rubric_items", [])
    tests_py = (item.get("resources") or {}).get("tests_py", "")
    if ge_code and hasattr(ge_code, "grade_code"):
        return ge_code.grade_code(
            question_id=question_id,
            rubric_items=rubric,
            file_arcnames=item.get("answer_file_arcnames", []),
            tests_py=tests_py
        )
    return {
        "question_id": question_id,
        "type": "code",
        "rubric_scores": [{"criteria": r["criteria"], "score": 0, "max_score": r["max_score"]} for r in rubric],
        "total_score": 0,
        "feedback": "Placeholder: code grader not wired."
    }


def _grade_numeric(item: Dict[str, Any]) -> Dict[str, Any]:
    question_id = item["question_id"]
    rubric = item.get("rubric_items", [])
    return {
        "question_id": question_id,
        "type": "numeric",
        "rubric_scores": [{"criteria": r["criteria"], "score": 0, "max_score": r["max_score"]} for r in rubric],
        "total_score": 0,
        "feedback": "Placeholder: numeric grader not wired."
    }


def _grade_mcq(item: Dict[str, Any]) -> Dict[str, Any]:
    question_id = item["question_id"]
    rubric = item.get("rubric_items", [])
    correct = set((item.get("meta") or {}).get("mcq_correct", []))
    selected = set((item.get("answer_mcq") or {}).get("selected", []))
    max_score = sum(r["max_score"] for r in rubric) or 1
    if not correct:
        score = 0
    elif len(correct) == 1:
        score = max_score if selected == correct else 0
    else:
        tp = len(correct & selected)
        fp = len(selected - correct)
        fn = len(correct - selected)
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        score = round(max_score * f1, 4)
    return {
        "question_id": question_id,
        "type": "mcq",
        "rubric_scores": [{"criteria": (rubric[0]["criteria"] if rubric else "MCQ"), "score": score, "max_score": max_score}],
        "total_score": score,
        "feedback": f"Correct={sorted(correct)}, Selected={sorted(selected)}"
    }


def build_items(ingest_manifest: Dict[str, Any], question_manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    return build_items_from_ingest(ingest_manifest=ingest_manifest, question_manifest=question_manifest)


def grade_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for it in items:
        kind = _route_item(it)
        if kind == "free_text":
            res = _grade_free_text(it)
        elif kind == "code":
            res = _grade_code(it)
        elif kind == "numeric":
            res = _grade_numeric(it)
        elif kind == "mcq":
            res = _grade_mcq(it)
        else:
            res = {
                "question_id": it["question_id"],
                "type": kind,
                "rubric_scores": [],
                "total_score": 0,
                "feedback": "Unknown type."
            }
        res["question_id"] = it["question_id"]
        res["_student_raw_folder"] = it["student"]["raw_folder"]
        results.append(res)
    return results


def group_results_by_student(items: List[Dict[str, Any]], graded: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_student: Dict[str, Dict[str, Any]] = {}
    for it in items:
        s = it["student"]["raw_folder"]
        if s not in by_student:
            by_student[s] = {
                "raw_folder": s,
                "overall_score": 0,
                "items": [],
                "instructor_note": ""
            }
    for gr in graded:
        s = gr["_student_raw_folder"]
        if "total_score" not in gr or gr["total_score"] is None:
            gr["total_score"] = round(sum((rs.get("score", 0) for rs in gr.get("rubric_scores", []))), 4)
        by_student[s]["items"].append({
            "question_id": gr.get("question_id", "Q?"),
            "total_score": gr.get("total_score", 0),
            "rubric_scores": gr.get("rubric_scores", []),
            "feedback_text": gr.get("feedback", ""),
            "explanation": gr.get("explanation", "")
        })
    for s, payload in by_student.items():
        payload["overall_score"] = round(sum(it["total_score"] for it in payload["items"]), 4)
    return list(by_student.values())


def persist_results_to_db(_graded_by_student: List[Dict[str, Any]]) -> None:
    """
    Hook to your DB if desired (left as a stub to avoid accidental writes).
    """
    # from database.postgres_handler import PostgresHandler
    # db = PostgresHandler(...)
    # db.save_results(_graded_by_student)
    return
