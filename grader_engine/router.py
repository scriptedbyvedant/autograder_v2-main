from typing import Dict
import re

TYPES = ["mcq", "short", "essay", "math", "code", "table_reasoning", "diagram"]

def classify(question_text: str) -> Dict:
    """
    Heuristic router. You can swap this later with an LLM call.
    """
    q = question_text or ""
    ql = q.lower()

    # Defaults
    qtype = "essay"
    if len(ql) < 160:
        qtype = "short"

    # Multiple choice
    if re.search(r"\b(a\)|b\)|c\)|d\))", ql) or "multiple choice" in ql:
        qtype = "mcq"

    # Code fences
    if "```" in q:
        qtype = "code"

    # LaTeX cues
    if re.search(r"\$[^$]+\$|\\\(|\\\)|\\\[|\\\]", q):
        qtype = "math"

    topic = (re.findall(r"[A-Za-z]{4,}", ql) or ["general"])[0]
    return {"type": qtype, "topic": topic, "points": 10}
