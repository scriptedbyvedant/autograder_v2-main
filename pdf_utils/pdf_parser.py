import fitz  # PyMuPDF
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from io import BytesIO


# --- Data model for downstream pipeline --------------------------------------
@dataclass
class Block:
    q_id: str
    block_type: str           # 'question' | 'ideal' | 'rubric' | 'student'
    modality: List[str]       # ['text','math','code','table','image']
    text: str = ""
    latex: List[str] = None
    code: Optional[Dict[str, str]] = None     # {"lang": "...", "content": "..."}
    tables: Optional[List[Dict[str, str]]] = None
    images: Optional[List[str]] = None
    bbox: Optional[List[float]] = None
    page: int = 0


MATH_PATTERN = re.compile(r"\$[^$]+\$|\\\([^\)]+\\\)|\\\[[^\]]+\\\]", re.MULTILINE)
CODE_FENCE   = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)


def extract_text_from_pdf(pdf_file) -> str:
    """
    Extract raw text from uploaded PDF (file-like object).
    NOTE: we seek(0) so callers can reuse the same BytesIO.
    """
    try:
        pdf_file.seek(0)
    except Exception:
        pass
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def extract_blocks_from_pdf(pdf_file) -> List[Block]:
    """
    Robust(ish) layout-aware extraction that keeps page segmentation,
    detects inline/display LaTeX, and fenced code blocks.
    """
    try:
        pdf_file.seek(0)
    except Exception:
        pass
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    blocks: List[Block] = []
    qn = 0

    try:
        for pno, page in enumerate(doc):
            text = page.get_text("text")
            if not text.strip():
                continue

            # Segment by common headers: Q1:, Question 1, Aufgabe 1, etc.
            chunks = re.split(
                r"(?mi)^(?:Q(?:uestion)?\s*\d+[:.)]|Aufgabe\s*\d+[:.)]|Frage\s*\d+[:.)])",
                text
            )

            # If no obvious markers, treat page as one question chunk
            if len(chunks) <= 1:
                chunks = [text]

            for chunk in chunks:
                c = chunk.strip()
                if not c:
                    continue

                qn += 1
                qid = f"Q{qn}"

                latex = [m.group(0) for m in MATH_PATTERN.finditer(c)]
                code_m = list(CODE_FENCE.finditer(c))
                code = None
                modality = ["text"]
                if latex:
                    modality.append("math")
                if code_m:
                    lang = (code_m[0].group(1) or "text").lower()
                    code = {"lang": lang, "content": code_m[0].group(2)}
                    modality.append("code")

                blocks.append(
                    Block(
                        q_id=qid,
                        block_type="question",
                        modality=list(dict.fromkeys(modality)),
                        text=c,
                        latex=latex or [],
                        code=code,
                        page=pno
                    )
                )
        return blocks
    finally:
        doc.close()


def parse_professor_pdf(text: str) -> Dict[str, Any]:
    """
    Parse an instructor PDF (already text) into sections for questions/ideals/rubrics.
    Flexible: supports English/German keywords and numbered sections.

    Returns: {
      "questions": { "Q1": "...", ... },
      "ideals":    { "Q1": "...", ... },
      "rubrics":   { "Q1": { ... }, ... }
    }
    """
    questions: Dict[str, str] = {}
    ideals: Dict[str, str] = {}
    rubrics: Dict[str, Any] = {}

    # Questions
    q_matches = re.finditer(
        r"(?mi)^(?:Q(?:uestion)?|Aufgabe)\s*(\d+)\s*[:.)]\s*(.*?)(?=^(?:Q(?:uestion)?|Aufgabe)\s*\d+|^Ideal\s*(?:Answer|Antwort)|^(?:Rubric|Bewertung)|$)",
        text, re.S | re.M
    )
    for m in q_matches:
        questions[f"Q{m.group(1)}"] = m.group(2).strip()

    # Ideals
    i_matches = re.finditer(
        r"(?mi)^Ideal\s*(?:Answer|Antwort)\s*(\d+)\s*[:.)]\s*(.*?)(?=^Ideal\s*(?:Answer|Antwort)|^(?:Rubric|Bewertung)|^(?:Q(?:uestion)?|Aufgabe)\s*\d+|$)",
        text, re.S | re.M
    )
    for m in i_matches:
        ideals[f"Q{m.group(1)}"] = m.group(2).strip()

    # Rubrics: allow inline JSON or bullet lists; keep raw text if not JSON
    r_matches = re.finditer(
        r"(?mi)^(?:Rubric|Bewertung(?:skriterien)?)\s*(\d+)\s*[:.)]\s*(.*?)(?=^(?:Rubric|Bewertung)|^(?:Q(?:uestion)?|Aufgabe)\s*\d+|$)",
        text, re.S | re.M
    )
    for m in r_matches:
        raw = m.group(2).strip()
        try:
            import json
            rubrics[f"Q{m.group(1)}"] = json.loads(raw)
        except Exception:
            # Simple bullet -> JSON conversion (• item (n points))
            lines = [ln.strip("-• ").strip() for ln in raw.splitlines() if ln.strip()]
            criteria = []
            for ln in lines:
                mpts = re.search(r"\((\d+(?:\.\d+)?)\s*(?:pts?|points?|Punkte?)\)", ln, re.I)
                pts = float(mpts.group(1)) if mpts else 1.0
                crit = re.sub(r"\s*\(\d+(?:\.\d+)?\s*(?:pts?|points?|Punkte?)\)\s*$", "", ln).strip()
                criteria.append({"id": crit, "points": pts})
            rubrics[f"Q{m.group(1)}"] = {"criteria": criteria}

    return {"questions": questions, "ideals": ideals, "rubrics": rubrics}


def parse_student_pdf(text: str) -> Dict[str, Dict[str, str]]:
    """
    Parse a student submissions PDF. Accepts blocks like:

      Student 1:
      A1: ...
      A2: ...

      Student 2:
      A1: ...
      ...

    Returns: { "Student 1": { "A1": "...", "A2": "..." }, ... }
    """
    students: Dict[str, Dict[str, str]] = {}

    # Split by student headers, capturing the header token
    parts = re.split(r'(?m)^(Student\s*\d+\s*:|Studierende[rn]?\s*\d+\s*:)\s*', text)

    # parts = [<pre>, <label1>, <block1>, <label2>, <block2>, ...]
    for i in range(1, len(parts), 2):
        label = parts[i].rstrip(':').strip()
        block = parts[i + 1] if i + 1 < len(parts) else ""

        answers: Dict[str, str] = {}
        # Capture A1:/F1: style answers until next answer or next student block
        for m in re.finditer(
            r'(?ms)^(A\d+|F\d+)\s*:\s*(.*?)(?=^\s*(?:A\d+|F\d+)\s*:|^\s*(?:Student\s*\d+|Studierende[rn]?\s*\d+)\s*:|\Z)',
            block
        ):
            answers[m.group(1)] = m.group(2).strip()

        students[label] = answers

    return students


def blocks_to_json(blocks: List[Block]) -> List[Dict[str, Any]]:
    return [asdict(b) for b in blocks]


# ---------------- NEW: helper for single-PDF multi-student grading ------------

def build_students_payload_from_pdf(single_pdf_filelike) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Given a single PDF (file-like) that contains multiple students (Student 1:, Student 2:, ...),
    return a payload suitable for the downstream grading pipeline:

        {
          "Student 1": { "A1": [ {type:"text", content:"..." } ], "A2": [ ... ] },
          "Student 2": { ... }
        }

    Each answer string becomes a simple text block. If you later support images/code per
    answer, you can extend the value lists accordingly.
    """
    # ensure fresh read if caller reuses the same BytesIO
    try:
        single_pdf_filelike.seek(0)
    except Exception:
        pass

    raw_text = extract_text_from_pdf(single_pdf_filelike)
    students_answers = parse_student_pdf(raw_text)

    students_payload: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for student_label, answers in students_answers.items():
        students_payload[student_label] = {
            ans_id: [{"type": "text", "content": ans_text}]
            for ans_id, ans_text in answers.items()
        }

    return students_payload
