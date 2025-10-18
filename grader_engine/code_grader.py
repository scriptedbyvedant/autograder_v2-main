# grader_engine/code_grader.py
"""
Universal code grading (Python) with safe subprocess and fallbacks.

- Primary scoring: run tests [{input, expected}] -> points by pass count.
- If NO tests are provided, we do two fallbacks to avoid hard 0s:
  (1) syntax check (compiles?): awards up to 20% of total rubric points
  (2) smoke run (no input): if it runs and prints non-empty stdout -> bump to 40%

Returns a tuple:
  ( total_points_awarded: float,
    per_criterion_breakdown: List[{"criteria": str, "score": float}],
    details: Dict[str, Any] )
"""
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import subprocess, tempfile, os, sys, textwrap

PYTHON_BIN = sys.executable

def _rubric_to_list_and_total(rubric_any) -> (List[Dict[str, Any]], int):
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
            rounded[i] = min(int(rubric_list[i].get("points", 0)), rounded[i] + 1); drift -= 1
        else:
            rounded[i] = max(0, rounded[i] - 1); drift += 1
        i = (i + 1) % len(rounded)
    return [{"criteria": r.get("criteria", ""), "score": float(sc)} for r, sc in zip(rubric_list, rounded)]

def _run(code: str, stdin_data: str, timeout_sec: int = 5) -> Tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "s.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            p = subprocess.run(
                [PYTHON_BIN, path],
                input=stdin_data.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_sec
            )
            return p.returncode, p.stdout.decode("utf-8").strip(), p.stderr.decode("utf-8").strip()
        except subprocess.TimeoutExpired:
            return 124, "", "Timeout"
        except Exception as e:
            return 1, "", f"Error: {e}"

def _syntax_ok(code: str) -> bool:
    try:
        compile(code, "<student>", "exec")
        return True
    except Exception:
        return False

def grade_code(
    student_code: str,
    tests: Optional[List[Dict[str, Any]]] = None,
    time_limit: int = 6,
    rubric: Optional[List[Dict[str, Any]]] = None
) -> Tuple[float, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns: (total_awarded, rubric_breakdown, details)
    """
    rubric = rubric or []
    rubric_list, total_points = _rubric_to_list_and_total(rubric)

    if (student_code or "").strip() == "":
        return 0.0, [{"criteria": r["criteria"], "score": 0.0} for r in rubric_list], {
            "reason": "blank", "passed": 0, "total": 0, "failures": []
        }

    tests = tests or []

    # If tests exist -> strict scoring by pass count
    if tests:
        passed = 0
        failures = []
        for t in tests:
            stdin_data = str(t.get("input", ""))
            expected = str(t.get("expected", t.get("output", ""))).strip()
            rc, out, err = _run(student_code, stdin_data, timeout_sec=time_limit)
            if rc == 0 and out == expected:
                passed += 1
            else:
                failures.append({"input": stdin_data, "expected": expected, "got": out, "stderr": err, "exit": rc})
        ratio = passed / len(tests)
        total_award = float(int(round(ratio * total_points)))
        breakdown = _proportional_scores(total_award, rubric_list)
        return total_award, breakdown, {"reason": "tests", "passed": passed, "total": len(tests), "failures": failures}

    # ---- No tests provided: fallbacks so we don't hard-zero good code ----
    # Fallback 1: syntax-only
    syn_ok = _syntax_ok(student_code)
    if syn_ok and total_points > 0:
        # award up to 20%
        twenty = max(1, int(round(0.2 * total_points)))
        # try smoke run
        rc, out, err = _run(student_code, "", timeout_sec=time_limit)
        if rc == 0 and out.strip():
            # code runs and prints something -> 40%
            award = max(twenty, int(round(0.4 * total_points)))
            reason = "smoke_run_output"
        elif rc == 0:
            award = twenty
            reason = "smoke_run_ok"
        else:
            award = twenty
            reason = f"syntax_ok_runtime_issue: {err[:120]}"
        breakdown = _proportional_scores(float(award), rubric_list)
        return float(award), breakdown, {"reason": reason, "passed": None, "total": None, "stderr": err if syn_ok else ""}

    # Nothing workable
    return 0.0, [{"criteria": r["criteria"], "score": 0.0} for r in rubric_list], {
        "reason": "no_tests_and_bad_code", "passed": 0, "total": 0, "failures": []
    }
