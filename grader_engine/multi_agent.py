# grader_engine/multi_agent.py
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Union
import statistics
import json
import re

from .rag_integration import retrieve_context
from .text_grader import grade_answer
from .math_grader import grade_math
from .code_grader import grade_code

# Optional external router; if missing we fallback to simple heuristics
try:
    from .router import classify as _external_classify
except Exception:
    _external_classify = None


# ------------------------- routing helpers -------------------------

def _fallback_classify(text: str, has_latex: bool, has_code: bool) -> Dict[str, str]:
    """
    Very light heuristic when no external router is available.
    """
    if has_code:
        return {"type": "code"}
    if has_latex:
        return {"type": "math"}
    # quick textual hints
    if re.search(r"\b(code|python|java|c\+\+|function|class|def\s+)\b", text or "", re.I):
        return {"type": "code"}
    if re.search(r"[=^+\-*/]|\\frac|\\sum|\\int|\$", text or ""):
        return {"type": "math"}
    return {"type": "text"}


def classify(text: str, has_latex: bool, has_code: bool) -> Dict[str, str]:
    if _external_classify:
        try:
            return _external_classify(text)
        except Exception:
            pass
    return _fallback_classify(text, has_latex, has_code)


# ------------------------- normalization helpers -------------------------

def _as_uniform_grade(obj: Any) -> Dict[str, Any]:
    """
    Normalize various grader outputs to a common structure:
      { total: float, criteria: [{criteria,score}], uncertainty: float }
    Supports dict or (total, breakdown, ...) tuple from graders.
    """
    # tuple support (e.g., (total, breakdown, feedback/diagnostics))
    if isinstance(obj, (tuple, list)) and len(obj) >= 2:
        total = float(obj[0]) if obj[0] is not None else 0.0
        crit_list = obj[1] or []
        norm: List[Dict[str, Any]] = []

        # math breakdown: {"criteria": str, "score": int}
        # code breakdown: {"test": "Test 1", "score": 0/1}
        for c in crit_list:
            if isinstance(c, dict):
                if "criteria" in c:
                    nm = c.get("criteria", "")
                elif "test" in c:
                    nm = c.get("test", "")
                else:
                    nm = ""
                sc = c.get("score", 0)
                try:
                    sc = float(sc)
                except Exception:
                    sc = 0.0
                norm.append({"criteria": str(nm), "score": sc})

        return {"total": total, "criteria": norm, "uncertainty": 0.3}

    # dict support
    if isinstance(obj, dict):
        # total
        if "total" in obj:
            total = float(obj.get("total", 0.0))
        elif "total_score" in obj:
            total = float(obj.get("total_score", 0.0))
        else:
            total = 0.0

        # per-criterion list
        crits = obj.get("criteria") or obj.get("rubric") or obj.get("rubric_scores") or []
        norm: List[Dict[str, Any]] = []
        for c in crits or []:
            if isinstance(c, dict):
                name = c.get("criteria", c.get("id", c.get("test", "")))
                sc = c.get("score", 0)
                try:
                    sc = float(sc)
                except Exception:
                    sc = 0.0
                norm.append({"criteria": str(name), "score": sc})

        # uncertainty (optional)
        uncert = obj.get("uncertainty", obj.get("disagreement", 0.0))
        try:
            uncert = float(uncert)
        except Exception:
            uncert = 0.35

        return {"total": total, "criteria": norm, "uncertainty": uncert}

    # fallback
    return {"total": 0.0, "criteria": [], "uncertainty": 0.5}


def _distribute_total_to_rubric(total: float, rubric_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    If a grader returned only a total, spread it across rubric items by weight.
    """
    if not rubric_list:
        return []

    pts = [float(r.get("points", 0)) for r in rubric_list]
    possible = sum(pts) or 1.0
    raw = [total * (p / possible) for p in pts]
    rounded = [int(round(x)) for x in raw]

    # fix rounding drift
    drift = int(round(total)) - sum(rounded)
    i = 0
    while drift != 0 and rubric_list:
        if drift > 0:
            rounded[i] = min(int(pts[i]), rounded[i] + 1)
            drift -= 1
        else:
            rounded[i] = max(0, rounded[i] - 1)
            drift += 1
        i = (i + 1) % len(rounded)

    out = []
    for r, sc in zip(rubric_list, rounded):
        maxp = int(round(float(r.get("points", 0))))
        out.append({"criteria": r.get("criteria", ""), "score": float(max(0, min(sc, maxp)))})
    return out


def _try_json(raw: Any):
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return None


def _ensure_rubric_list_and_dict(rubric_any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Accept rubric as list or dict; return (list, dict) pair.
    """
    if isinstance(rubric_any, dict) and isinstance(rubric_any.get("criteria"), list):
        return rubric_any["criteria"], rubric_any
    if isinstance(rubric_any, list):
        return rubric_any, {"criteria": rubric_any}
    parsed = _try_json(rubric_any)
    if isinstance(parsed, dict) and isinstance(parsed.get("criteria"), list):
        return parsed["criteria"], parsed
    if isinstance(parsed, list):
        return parsed, {"criteria": parsed}
    return [], {"criteria": []}


# ------------------------- fusion -------------------------

def fuse(grades: List[Any]) -> Dict[str, Any]:
    """
    Combine multiple grader outputs by averaging totals and tracking disagreement.
    Accepts tuples (total, breakdown, ...) or dicts; normalizes first.
    """
    unif = [_as_uniform_grade(g) for g in grades]
    totals = [g["total"] for g in unif]
    if not totals:
        return {"final": {"total": 0.0, "per_criterion": []}, "disagreement": 1.0, "needs_review": True}

    mean_total = sum(totals) / len(totals)
    disagreement = statistics.pstdev(totals) if len(totals) > 1 else 0.0
    needs_review = disagreement > 2.0 or any(g["uncertainty"] > 0.5 for g in unif)

    # Prefer criteria list from the first grader if present
    per_criterion = unif[0]["criteria"]

    return {
        "final": {"total": round(mean_total, 2), "per_criterion": per_criterion},
        "disagreement": disagreement,
        "needs_review": needs_review,
    }


# ------------------------- main entry -------------------------

def grade_block(
    q_id: str,
    text: str,
    latex: List[str],
    code: Optional[Dict[str, str]],
    rubric_json: Optional[Any] = None,
    ideal_text_or_expr: Optional[str] = None,
    tests: Optional[List[Dict[str, Any]]] = None,
    client_primary: Optional[Any] = None,   # kept for API compatibility (unused)
    client_skeptic: Optional[Any] = None,   # kept for API compatibility (unused)
    return_debug: bool = False
) -> Dict[str, Any]:
    """
    One-stop grading for a single "question block".
    - Auto-routes to math/code/text graders.
    - Uses RAG to fill/augment rubric/ideal if missing.
    - Returns:
        {
          "final": {"total": float, "per_criterion": [...]},
          "disagreement": float,
          "needs_review": bool,
          "kind": "math|code|text",
          "debug": {...}                 # only if return_debug=True
        }
    """
    has_latex = bool(latex)
    has_code = bool(code and (code.get("content") or "").strip())
    meta = classify(text or "", has_latex, has_code)

    # RAG context for the question
    ctx = retrieve_context(q_id, text or "", k=3)

    # Rubric and ideal-answer fallback via RAG
    rag_rubric = _try_json(ctx.get("rubric")) if ctx.get("rubric") is not None else None
    rubric_any = rubric_json if rubric_json else (rag_rubric if rag_rubric is not None else [])
    rubric_list, rubric_dict = _ensure_rubric_list_and_dict(rubric_any)

    ideal = (ideal_text_or_expr or ctx.get("ideal") or "").strip()

    # Prepare debug shell
    dbg: Dict[str, Any] = {}
    dbg["router_type"] = meta.get("type")
    if return_debug:
        # minimal peek at RAG (without huge blobs)
        dbg["rag"] = {
            "ideal_present": bool(ideal),
            "rubric_items": len(rubric_list),
            "exemplars_n": len((ctx.get("exemplars") or []))
        }

    # -------------------- Math path --------------------
    if meta["type"] == "math":
        # Student provided LaTeX (or detected math) in `latex[0]`, else fall back to text
        student_expr_text = (latex[0].strip() if has_latex else (text or "")) or ""
        ideal_expr_text = ideal or student_expr_text  # fail-safe if ideal is missing

        g1 = grade_math(student_expr_text, ideal_expr_text, rubric_list)
        g2 = grade_math(student_expr_text, ideal_expr_text, rubric_list)  # light ensemble

        fused = fuse([g1, g2])
        if not fused["final"]["per_criterion"]:
            fused["final"]["per_criterion"] = _distribute_total_to_rubric(fused["final"]["total"], rubric_list)
        fused["kind"] = "math"

        if return_debug:
            # math grader returns (total, breakdown, details)
            _, _, d1 = g1
            dbg["math"] = {
                "student_input": student_expr_text[:1000],
                "ideal_input": ideal_expr_text[:1000],
                "details": d1
            }
            fused["debug"] = dbg
        return fused

    # -------------------- Code path --------------------
    if meta["type"] == "code" and has_code:
        code_content = code.get("content", "")
        code_lang = code.get("lang", "python")

        # Our code grader expects (student_code, tests?, time_limit?, rubric?)
        g1 = grade_code(code_content, tests or [], 6, rubric_list)

        fused = fuse([g1])
        if not fused["final"]["per_criterion"]:
            fused["final"]["per_criterion"] = _distribute_total_to_rubric(fused["final"]["total"], rubric_list)
        fused["kind"] = "code"

        if return_debug:
            # code grader returns (total, breakdown, details)
            _, _, d1 = g1
            # only show up to first 5 tests to keep UI tidy
            tests_preview = (tests or [])[:5]
            dbg["code"] = {
                "lang": code_lang,
                "student_code_preview": code_content[:1000],
                "tests_preview": tests_preview,
                "details": d1
            }
            fused["debug"] = dbg
        return fused

    # -------------------- Text (LLM) path --------------------
    # Use exemplars/ideal from RAG for stronger grading context
    g1_raw = grade_answer(
        question=text or "",
        ideal_answer=ideal or "",
        rubric=rubric_list,
        student_answer=text or "",
        language="English",
        model_name=None,
        rag_context=ctx,
        return_debug=return_debug
    )
    g2_raw = grade_answer(
        question=text or "",
        ideal_answer=ideal or "",
        rubric=rubric_list,
        student_answer=text or "",
        language="English",
        model_name=None,
        rag_context=ctx,
        return_debug=return_debug
    )

    g1 = {"total_score": g1_raw.get("total_score", 0.0), "rubric_scores": g1_raw.get("rubric_scores", []), "uncertainty": 0.35}
    g2 = {"total_score": g2_raw.get("total_score", 0.0), "rubric_scores": g2_raw.get("rubric_scores", []), "uncertainty": 0.35}

    fused = fuse([g1, g2])
    if not fused["final"]["per_criterion"]:
        fused["final"]["per_criterion"] = _distribute_total_to_rubric(fused["final"]["total"], rubric_list)
    fused["kind"] = "text"

    if return_debug:
        # Prefer first run's prompt/output
        dbg["llm"] = g1_raw.get("debug", {})
        fused["debug"] = dbg
    return fused
