import textwrap

from pdf_utils.pdf_parser import parse_professor_pdf, parse_student_pdf


def test_parse_professor_pdf_sections():
    sample = textwrap.dedent(
        """
        Q1: Define artificial intelligence.
        Ideal Answer 1: The field of building systems that can reason, learn, and act autonomously.
        Rubric 1:
        - Completeness (3 points)
        - Clarity (2 points)

        Q2: Explain gradient descent.
        Ideal Answer 2: An iterative optimisation algorithm that updates parameters in the direction of the negative gradient.
        Rubric 2: {"criteria": [{"id": "Accuracy", "points": 5}]}
        """
    )

    parsed = parse_professor_pdf(sample)

    assert parsed["questions"]["Q1"].startswith("Define artificial intelligence")
    assert "gradient descent" in parsed["questions"]["Q2"].lower()
    assert parsed["ideals"]["Q2"].startswith("An iterative optimisation")

    rubric_q1 = parsed["rubrics"]["Q1"]
    assert "criteria" in rubric_q1 and len(rubric_q1["criteria"]) == 2
    assert rubric_q1["criteria"][0]["points"] == 3

    rubric_q2 = parsed["rubrics"]["Q2"]
    assert rubric_q2["criteria"][0]["id"] == "Accuracy"


def test_parse_student_pdf_blocks():
    sample = textwrap.dedent(
        """
        Student 1:
        A1: AI means building machines that can reason.
        A2: Gradient descent reduces the loss using gradients.

        Student 2:
        A1: Intelligent behaviour in software.
        A2: It iteratively updates weights.
        """
    )

    parsed = parse_student_pdf(sample)

    assert "Student 1" in parsed and "Student 2" in parsed
    assert parsed["Student 1"]["A1"].startswith("AI means")
    assert parsed["Student 2"]["A2"].startswith("It iteratively")
