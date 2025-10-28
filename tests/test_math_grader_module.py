import pytest

try:
    import sympy  # noqa: F401
    HAS_SYMPY = True
except Exception:
    HAS_SYMPY = False

from grader_engine.math_grader import grade_math


@pytest.mark.skipif(not HAS_SYMPY, reason="SymPy required for math grading")
def test_grade_math_exact_match():
    rubric = [{"criteria": "Algebra", "points": 10}]
    total, breakdown, details = grade_math("2*x + 3", "$2x + 3$", rubric)

    assert total == 10
    assert breakdown[0]["score"] == 10
    assert details["reason"] == "exact_match"
    assert details["symbolic_equal"] is True


@pytest.mark.skipif(not HAS_SYMPY, reason="SymPy required for math grading")
def test_grade_math_parse_failure_returns_zero():
    rubric = [{"criteria": "Algebra", "points": 8}]
    total, breakdown, details = grade_math("???", "x + 1", rubric)

    assert total == 0
    assert all(item["score"] == 0 for item in breakdown)
    assert details["reason"] == "parse_failed"
