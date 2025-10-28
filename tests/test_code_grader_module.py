from grader_engine.code_grader import grade_code


def test_grade_code_with_unit_tests():
    student_code = """\nimport sys\nvalue = int(sys.stdin.read().strip() or 0)\nprint(value * value)\n"""
    rubric = [{"criteria": "Correctness", "points": 5}]
    tests = [
        {"input": "2", "expected": "4"},
        {"input": "5", "expected": "25"},
    ]

    total, breakdown, details = grade_code(student_code, tests=tests, rubric=rubric)

    assert total == 5
    assert breakdown[0]["score"] == 5
    assert details["passed"] == 2 and details["total"] == 2


def test_grade_code_fallback_awards_partial_credit():
    student_code = "print('hello world')"
    rubric = [{"criteria": "Output", "points": 5}]

    total, breakdown, details = grade_code(student_code, tests=[], rubric=rubric)

    # 40% of 5 points -> 2 (minimum partial credit when smoke run prints output)
    assert total >= 2
    assert breakdown[0]["score"] >= 2
    assert details["reason"].startswith("smoke_run")
