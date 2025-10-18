
# grader_engine/__init__.py

from .text_grader import grade_answer
from .explainer import generate_explanation
from .pdf_parser import extract_text_from_pdf

__all__ = [
    "grade_answer",
    "generate_explanation",
    "extract_text_from_pdf"
]
