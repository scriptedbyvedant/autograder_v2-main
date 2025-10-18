# grader_engine/math_grader.py
"""
Universal math grading with robust parsing + partial credit.

- Accepts student/ideal as LaTeX or plain math (handles $, \(...\), \[...\], $$...$$).
- If LaTeX parsing is unavailable or fails, falls back to smart string normalization
  -> SymPy parsing.
- Full credit when symbolic equality holds.
- Otherwise, numeric sampling across free symbols -> fraction of correctness.
- Converts fraction to points; proportionally distributes across rubric items.
- Never silently returns 0 unless both parsing and numeric checks fail and rubric has 0 pts.

Returns a tuple:
  ( total_points_awarded: float,
    per_criterion_breakdown: List[{"criteria": str, "score": float}],
    details: Dict[str, Any] )
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple
import random
import re

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr
    try:
        from sympy.parsing.latex import parse_latex
        _HAS_PARSE_LATEX = True
    except Exception:
        _HAS_PARSE_LATEX = False
except Exception:
    sp = None
    _HAS_PARSE_LATEX = False


# --------- small utils ---------

def _ensure_sympy():
    if sp is None:
        raise RuntimeError(
            "SymPy is required. Install with: pip install sympy antlr4-python3-runtime"
        )

_LATEX_WRAP_RE = re.compile(r"^\s*(\${1,2}|\\\(|\\\[)\s*(.*?)\s*(\${1,2}|\\\)|\\\])\s*$", re.S)

def _unwrap_math(s: str) -> str:
    if not s:
        return ""
    m = _LATEX_WRAP_RE.match(s.strip())
    return m.group(2) if m else s.strip()

def _normalize_latex_like(s: str) -> str:
    """Turn very common LaTeX into sympifiable text if parse_latex isn't available."""
    if not s:
        return ""
    # strip wrappers
    s = _unwrap_math(s)
    # Remove \left \right, thin spaces, \,
    s = re.sub(r"\\left|\\right|\\,", "", s)
    s = s.replace(r"\cdot", "*").replace(r"\times", "*").replace(r"\div", "/")
    # \frac{a}{b} -> (a)/(b)
    def _frac_sub(m):
        return f"({m.group(1)})/({m.group(2)})"
    s = re.sub(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}", _frac_sub, s)
    # \sqrt{a} -> (a)**0.5
    s = re.sub(r"\\sqrt\s*\{([^{}]+)\}", r"(\1)**0.5", s)
    # Replace ^ with ** (only when not already **)
    s = re.sub(r"\^", "**", s)
    # remove \text{...}
    s = re.sub(r"\\text\s*\{[^{}]*\}", "", s)
    # bracket groups
    s = s.replace("{", "(").replace("}", ")")
    return s.strip()

def _parse_expr_text(s: str) -> sp.Expr | None:
    """Parse math from LaTeX OR plain. Robust to common issues."""
    _ensure_sympy()
    if not s:
        return None
    raw = s.strip()
    # handle "lhs = rhs" by moving to zero
    if "=" in raw and "==" not in raw:
        parts = raw.split("=")
        if len(parts) == 2:
            l = _parse_expr_text(parts[0])
            r = _parse_expr_text(parts[1])
            if l is not None and r is not None:
                try:
                    return sp.simplify(l - r)
                except Exception:
                    pass

    # Try native LaTeX if available and looks latex-y
    looks_latex = ("\\" in raw) or raw.startswith("$") or raw.endswith("$")
    if looks_latex and _HAS_PARSE_LATEX:
        try:
            return parse_latex(_unwrap_math(raw))
        except Exception:
            pass

    # Try normalization then sympify/parse_expr
    candid = _normalize_latex_like(raw)
    try:
        return parse_expr(candid, evaluate=True)
    except Exception:
        try:
            return sp.sympify(candid)
        except Exception:
            return None

def _rubric_to_list_and_total(rubric_any) -> Tuple[List[Dict[str, Any]], int]:
    if isinstance(rubric_any, dict) and isinstance(rubric_any.get("criteria"), list):
        lst = rubric_any["criteria"]
    elif isinstance(rubric_any, list):
        lst = rubric_any
    else:
        lst = []
    out, total = [], 0
    for c in lst:
        if isinstance(c, dict):
            pts = int(round(float(c.get("points", 0))))
            total += pts
            out.append({"criteria": str(c.get("criteria", "")), "points": pts})
    return out, total

def _proportional_scores(total_award: float, rubric_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pts = [float(r.get("points", 0)) for r in rubric_list]
    possible = sum(pts) or 1.0
    raw = [total_award * (p / possible) for p in pts]
    rounded = [int(round(x)) for x in raw]
    drift = int(round(total_award)) - sum(rounded)
    i = 0
    while drift != 0 and rubric_list:
        if drift > 0:
            rounded[i] = min(int(rubric_list[i].get("points", 0)), rounded[i] + 1)
            drift -= 1
        else:
            rounded[i] = max(0, rounded[i] - 1)
            drift += 1
        i = (i + 1) % len(rounded)
    return [{"criteria": r.get("criteria", ""), "score": float(sc)} for r, sc in zip(rubric_list, rounded)]

def _numeric_fraction_equal(a: sp.Expr, b: sp.Expr) -> float:
    """Sample up to 3 free symbols across safe points."""
    _ensure_sympy()
    vars_list = sorted(list((a.free_symbols | b.free_symbols)), key=lambda s: s.name)[:3]
    if not vars_list:
        try:
            return 1.0 if float(sp.N(sp.simplify(a - b))) == 0.0 else 0.0
        except Exception:
            return 0.0
    # sample
    trials = 32 if len(vars_list) == 1 else 48
    ok = 0
    points = [-3, -2, -1.5, -1, -0.5, -0.25, 0.5, 1, 1.5, 2, 3]
    for _ in range(trials):
        subs = {}
        for v in vars_list:
            subs[v] = random.choice(points)
        try:
            dv = sp.N(sp.simplify((a - b).subs(subs)))
            if abs(float(dv)) <= 1e-6:
                ok += 1
        except Exception:
            pass
    return ok / max(1, trials)


# --------- main entry ---------

def grade_math(
    student_input: str,
    ideal_answer: str,
    rubric: List[Dict[str, Any]]
) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns: (total_awarded, rubric_breakdown, details)
    """
    _ensure_sympy()
    rubric_list, total_points = _rubric_to_list_and_total(rubric)
    # If no rubric points, nothing to award
    if total_points <= 0:
        return 0.0, [{"criteria": r["criteria"], "score": 0.0} for r in rubric_list], {
            "reason": "rubric_total_zero", "symbolic_equal": False, "fraction": 0.0
        }

    # Parse both
    s_expr = _parse_expr_text(student_input or "")
    i_expr = _parse_expr_text(ideal_answer or "")

    if s_expr is None or i_expr is None:
        # Can't parse; award 0 but return reason
        return 0.0, [{"criteria": r["criteria"], "score": 0.0} for r in rubric_list], {
            "reason": "parse_failed", "symbolic_equal": False, "fraction": 0.0
        }

    # Try exact equality
    try:
        exact = bool(sp.simplify(sp.expand(s_expr) - sp.expand(i_expr)) == 0)
    except Exception:
        exact = False

    if exact:
        return float(total_points), [{"criteria": r["criteria"], "score": float(r["points"])} for r in rubric_list], {
            "reason": "exact_match", "symbolic_equal": True, "fraction": 1.0
        }

    # Fractional correctness by numeric sampling
    try:
        frac = _numeric_fraction_equal(s_expr, i_expr)
    except Exception:
        frac = 0.0

    # Convert fraction to awarded points. Be generous above a tiny threshold.
    # (Prevents everything being 0 for close-but-not-exact answers)
    raw_total = frac * total_points
    # If fraction is tiny but non-zero, nudge small partial credit (max 20%)
    if 0.05 < frac < 0.25:
        raw_total = max(raw_total, 0.2 * total_points)
    total_award = float(int(round(raw_total)))

    breakdown = _proportional_scores(total_award, rubric_list)
    return total_award, breakdown, {
        "reason": "numeric_sampling",
        "symbolic_equal": False,
        "fraction": float(frac),
        "free_symbols": [str(v) for v in sorted(list((s_expr.free_symbols | i_expr.free_symbols)), key=lambda s: s.name)[:3]],
    }
