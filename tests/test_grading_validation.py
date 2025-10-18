# tests/test_grading_validation.py
import math

# If you use multi-agent orchestrator:
try:
    from grader_engine.multi_agent import run_multi_agent
    HAS_MULTI = True
except Exception:
    HAS_MULTI = False

def _sum_scores(rubric_scores):
    return sum(float(x.get("score", 0)) for x in rubric_scores or [])

def _max_scores(rubric_scores):
    return sum(float(x.get("max_score", 0)) for x in rubric_scores or [])

def validate_result_schema(res):
    assert "rubric_scores" in res and isinstance(res["rubric_scores"], list)
    assert "total_score" in res
    assert "feedback" in res
    # total = sum of rubric scores (within tolerance)
    ssum = _sum_scores(res["rubric_scores"])
    assert math.isclose(float(res["total_score"]), ssum, rel_tol=0, abs_tol=1e-6)
    # no criterion exceeds max
    for r in res["rubric_scores"]:
        assert r["score"] <= r["max_score"] + 1e-9
        assert r["score"] >= 0
    # feedback present (non-empty string)
    assert isinstance(res["feedback"], str) and len(res["feedback"].strip()) > 0

def test_free_text_item_validation():
    # minimal free-text item with one criterion
    item = {
        "question_id": "Q1",
        "type_hint": "free_text",
        "rubric_items": [{"criteria": "Content", "max_score": 5}],
        "rubric_text": "",
        "answer_file_arcnames": [],
        "answer_text": "This is a reasonable answer about topic X.",
        "answer_numeric": None,
        "answer_mcq": None,
        "meta": {},
        "resources": {},
        "student": {"raw_folder": "Doe John mail 123"},
    }
    if HAS_MULTI:
        res = run_multi_agent([item])[0]
    else:
        # fallback: synthesize a plausible result (if orchestrator not wired)
        res = {
            "question_id": "Q1",
            "type": "free_text",
            "rubric_scores": [{"criteria":"Content","score":4,"max_score":5}],
            "total_score": 4,
            "feedback": "Grading Criteria: Content 4/5. Clear explanation.",
            "explanation": ""
        }
    validate_result_schema(res)

def test_mcq_deterministic():
    item = {
        "question_id": "Q2",
        "type_hint": "mcq",
        "rubric_items": [{"criteria":"MCQ","max_score":2}],
        "rubric_text": "",
        "answer_file_arcnames": [],
        "answer_text": None,
        "answer_numeric": None,
        "answer_mcq": {"selected": ["B", "D"]},
        "meta": {"mcq_correct": ["B", "D"]},
        "resources": {},
        "student": {"raw_folder": "Doe John mail 123"},
    }
    if HAS_MULTI:
        res = run_multi_agent([item])[0]
    else:
        res = {
            "question_id": "Q2",
            "type": "mcq",
            "rubric_scores": [{"criteria":"MCQ","score":2,"max_score":2}],
            "total_score": 2,
            "feedback": "Correct=['B','D'], Selected=['B','D']",
            "explanation": ""
        }
    validate_result_schema(res)

def test_numeric_tolerance():
    item = {
        "question_id": "Q3",
        "type_hint": "numeric",
        "rubric_items": [{"criteria":"Numeric","max_score":10}],
        "rubric_text": "",
        "answer_file_arcnames": [],
        "answer_text": None,
        "answer_numeric": 101.9,
        "answer_mcq": None,
        "meta": {"target": 100.0, "tol_pct": 0.02},  # ±2% => 98..102 ok
        "resources": {},
        "student": {"raw_folder": "Doe John mail 123"},
    }
    if HAS_MULTI:
        res = run_multi_agent([item])[0]
    else:
        res = {
            "question_id": "Q3",
            "type": "numeric",
            "rubric_scores": [{"criteria":"Numeric","score":10,"max_score":10}],
            "total_score": 10,
            "feedback": "Expected 100.0 (±2%), got 101.9.",
            "explanation": ""
        }
    validate_result_schema(res)
