import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import letter  # kept in case other pages import/use
from reportlab.pdfgen import canvas         # kept in case other pages import/use
import re
import json
from typing import Dict, List, Any
import fitz  # PyMuPDF

from grader_engine.pdf_parser_multimodal import extract_multimodal_content_from_pdf
from grader_engine.multimodal_rag import MultimodalVectorStore
from ilias_utils.zip_parser import parse_ilias_zip, IngestResult
from ilias_utils.feedback_generator import FeedbackZipGenerator


# =============================== AUTH CHECK ===================================
if "logged_in_prof" not in st.session_state:
    st.warning("Please login first to access this page.", icon="🔒")
    st.stop()
prof = st.session_state["logged_in_prof"]


# =============================== PDF UTILS ====================================
def extract_text_from_pdf(pdf_file: BytesIO) -> str:
    """
    Extract raw text from uploaded PDF (file-like object).
    NOTE: Requires the real PyMuPDF package (pip install PyMuPDF).
    """
    try:
        pdf_file.seek(0)
    except Exception:
        pass
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        return "\n".join(page.get_text("text") for page in doc)


# ====================== PROFESSOR PDF PARSING (ROBUST) ========================
def _clean_invisibles(s: str) -> str:
    # Replace NBSP with space; strip zero-width chars & BOM
    s = s.replace("\u00A0", " ")
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)
    return s


def normalize_professor_headings(text: str) -> str:
    """
    Normalize headings like:
      'Q1 (MCQ):'        -> 'Q1:'
      'Question 2 (SA):' -> 'Question 2:'
      'Aufgabe 3 (Teil):'-> 'Aufgabe 3:'
    Also makes the colon optional.
    """
    text = re.sub(r'(?mi)^(Q(?:uestion)?)\s*(\d+)\s*\([^)]*\)\s*:?', r'\1 \2:', text)
    text = re.sub(r'(?mi)^(Aufgabe)\s*(\d+)\s*\([^)]*\)\s*:?', r'\1 \2:', text)
    return text


def parse_professor_pdf(text: str) -> Dict:
    """
    Parse an instructor PDF (already text) into sections for questions/ideals/rubrics.
    Flexible across English/German and tolerant to formatting noise.

    Returns:
      {
        "professor": "...", "course": "...", "session": "...", "assignment_no": "...",
        "questions": [
          {"id": "Q1", "question": "...", "ideal_answer": "...",
           "rubric": [{"criteria": "...", "points": 2}, ...]},
          ...
        ]
      }
    """
    text = _clean_invisibles(text)
    text = normalize_professor_headings(text)

    prof_info: Dict[str, Any] = {}
    patterns = {
        "professor": r"(Professor(?:in)?):\s*(.+)",
        "course": r"(Course|Kurs):\s*(.+)",
        "session": r"(Session|Sitzung):\s*(.+)",
        "assignment_no": r"(Assignment(?: No)?|Aufgabe(?:n)?(?: Nr)?):\s*([^\n]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            prof_info[key] = m.group(2).strip()

    # Split into question blocks; accept leading spaces and 'Q 1:' or 'Aufgabe 1:'
    blocks = re.split(r'(?mi)^\s*(Q\s*\d+\s*:|Aufgabe\s*\d+\s*:)\s*', text)

    questions: List[Dict] = []
    for i in range(1, len(blocks), 2):
        raw_hdr = blocks[i]
        block = blocks[i + 1] if i + 1 < len(blocks) else ""

        # Normalize header to "Q<n>"
        hdr_num = re.search(r'(?i)(?:Q|Aufgabe)\s*(\d+)', raw_hdr)
        if not hdr_num:
            continue
        qid = f"Q{hdr_num.group(1)}"

        # QUESTION: prefer explicit label; fallback = everything until Ideal/Rubric
        q_match = re.search(
            r'(?:^|\n)(?:Question|Frage)\s*:\s*(.*?)(?=\n(?:Ideal\s*(?:Answer|Antwort)\s*:)|\n(?:Rubric|Bewertungskriterien)\s*:|\Z)',
            block, re.S | re.IGNORECASE
        )
        if q_match:
            question_text = q_match.group(1).strip()
        else:
            tmp = re.split(
                r'(?mi)\n(?:Ideal\s*(?:Answer|Antwort)\s*:|(?:Rubric|Bewertungskriterien)\s*:)',
                block, maxsplit=1
            )
            question_text = tmp[0].strip() if tmp else block.strip()

        # IDEAL ANSWER (optional)
        ia_match = re.search(
            r'(?:^|\n)(?:Ideal\s*(?:Answer|Antwort))\s*:\s*(.*?)(?=\n\s*(?:Rubric|Bewertungskriterien)\s*:|\Z)',
            block, re.S | re.IGNORECASE
        )
        ideal_answer = ia_match.group(1).strip() if ia_match else ""

        # RUBRIC (JSON or bullet list)
        rubric_list: List[Dict[str, int]] = []
        r_match = re.search(
            r'(?:^|\n)(?:Rubric|Bewertungskriterien)\s*:\s*(.*)$',
            block, re.S | re.IGNORECASE
        )
        if r_match:
            rubric_text = r_match.group(1).strip()
            # Try JSON first
            try:
                parsed = json.loads(rubric_text)
                if isinstance(parsed, dict) and "criteria" in parsed:
                    for crit in parsed.get("criteria", []):
                        if isinstance(crit, dict) and "criteria" in crit and "points" in crit:
                            rubric_list.append({"criteria": crit["criteria"], "points": int(crit["points"])})
                elif isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "criteria" in item and "points" in item:
                            rubric_list.append({"criteria": item["criteria"], "points": int(item["points"])})
            except Exception:
                # Bullet list lines like: "- Correct def (2 pts)"
                for line in rubric_text.splitlines():
                    line = line.strip()
                    if not line or not line.lstrip().startswith('-'):
                        continue
                    mpts = re.search(r'\(\s*(\d+(?:\.\d+)?)\s*(?:points?|pts?|pt|Punkte?)\s*\)\s*$', line, re.IGNORECASE)
                    pts = float(mpts.group(1)) if mpts else 0.0
                    crit = re.sub(r'^\s*-\s*', '', line)
                    crit = re.sub(r'\s*\(\s*\d+(?:\.\d+)?\s*(?:points?|pts?|pt|Punkte?)\s*\)\s*$', '', crit).strip()
                    rubric_list.append({"criteria": crit, "points": int(pts)})

        questions.append({
            "id": qid,
            "question": question_text,
            "ideal_answer": ideal_answer,  # (string for now; normalized below)
            "rubric": rubric_list
        })

    prof_info["questions"] = questions
    return prof_info


# =================== SINGLE-PDF (MULTI-STUDENT) PARSER ========================
def parse_student_pdf(text: str) -> Dict[str, Dict[str, str]]:
    """
    For a single uploaded PDF that contains multiple students:

      Student 1:
      A1: ...
      A2: ...

      Student 2:
      A1: ...
      ...

    Returns:
      { "Student 1": { "A1": "...", "A2": "..." }, "Student 2": {...}, ... }
    """
    text = _clean_invisibles(text)
    students: Dict[str, Dict[str, str]] = {}

    # split by student header, capture the header token
    parts = re.split(r'(?m)^(Student\s*\d+\s*:|Studierende[rn]?\s*\d+\s*:)\s*', text)
    for i in range(1, len(parts), 2):
        label = parts[i].rstrip(':').strip()
        block = parts[i + 1] if i + 1 < len(parts) else ""

        answers: Dict[str, str] = {}
        # capture A1:/F1: until next answer or next student header
        for m in re.finditer(
            r'(?ms)^(A\d+|F\d+)\s*:\s*(.*?)(?=^\s*(?:A\d+|F\d+)\s*:|^\s*(?:Student\s*\d+|Studierende[rn]?\s*\d+)\s*:|\Z)',
            block
        ):
            answers[m.group(1)] = m.group(2).strip()

        students[label] = answers

    return students


# ==================== ZIP FLOW MULTIMODAL PROCESSOR ===========================
def process_student_data(content_blocks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses student answers from a list of multimodal content blocks.
    This is used for the ZIP flow and remains unchanged.
    """
    full_text = "\n".join(
        block.get("content", "") for block in content_blocks if block.get("type") == "text"
    ).strip()
    if not full_text:
        return {}

    # Find markers like Q1 / A1 / Answer 1 / Aufgabe 1 at the start of a line.
    answer_marker_regex = re.compile(r"(?im)^\s*(?:Q|A|Answer|Aufgabe)\s*(\d+)\s*[:.)]?")
    markers = list(answer_marker_regex.finditer(full_text))

    answers: Dict[str, List[Dict[str, Any]]] = {}
    for i, match in enumerate(markers):
        q_num = match.group(1)
        answer_key = f"A{q_num}"
        start_pos = match.end()
        end_pos = markers[i + 1].start() if i + 1 < len(markers) else len(full_text)
        answer_content = full_text[start_pos:end_pos].strip()
        if answer_content:
            answers[answer_key] = [{"type": "text", "content": answer_content}]
    return answers


# ================= NORMALIZE FOR UI + GRADER (small but crucial) ===============
def _normalize_prof_info_for_ui_and_grader(prof_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    - Ensure ideal_answer is a list of blocks for the UI, and also provide a plain string
      'ideal_answer_text' for any grader logic that expects raw text.
    - Ensure rubric is a list of {"criteria": str, "points": int}; compute 'max_points'.
    """
    qs = prof_info.get("questions", []) or []
    for q in qs:
        # Ideal answer -> blocks + plain text
        ia = q.get("ideal_answer", "")
        if isinstance(ia, str):
            blocks = [{"type": "text", "content": ia.strip()}] if ia.strip() else []
        elif isinstance(ia, list):
            blocks = []
            for blk in ia:
                if isinstance(blk, dict):
                    if "content" in blk:
                        blocks.append(blk)
                    else:
                        blocks.append({"type": "text", "content": str(blk)})
                else:
                    blocks.append({"type": "text", "content": str(blk)})
        else:
            blocks = []
        q["ideal_answer"] = blocks
        q["ideal_answer_text"] = " ".join(
            (b.get("content") or "") for b in blocks if isinstance(b, dict)
        ).strip()

        # Rubric normalize
        rb = q.get("rubric") or []
        if isinstance(rb, dict) and "criteria" in rb:
            rb = rb.get("criteria") or []
        norm = []
        for item in rb if isinstance(rb, list) else []:
            if isinstance(item, dict):
                crit = (item.get("criteria") or item.get("id") or "").strip()
                pts = item.get("points", 0)
            else:
                crit = str(item).strip()
                pts = 0
            try:
                pts = int(round(float(pts)))
            except Exception:
                pts = 0
            norm.append({"criteria": crit, "points": pts})
        q["rubric"] = norm
        q["max_points"] = sum(x["points"] for x in norm) if norm else 0

    prof_info["questions"] = qs
    return prof_info


# ============================ RAG SEEDING HELPER ==============================
def seed_multimodal_rag_from_professor(prof_info: Dict, prof_content_blocks: List[Dict], vs_instance: MultimodalVectorStore):
    vs_instance.index.reset()
    vs_instance.items.clear()
    vs_instance.by_q.clear()
    for i, block in enumerate(prof_content_blocks):
        doc_id = f"prof-block-{i}"
        for q in prof_info.get("questions", []):
            if qid := q.get("id"):
                vs_instance.add(doc_id, block['content'], block['type'], {"q_id": qid, "source": "professor"})
    for q in prof_info.get("questions", []):
        if not (qid := q.get("id")):
            continue
        if rubric := q.get("rubric"):
            vs_instance.add(f"{qid}-rubric", json.dumps(rubric, ensure_ascii=False), "text", {"type": "rubric", "q_id": qid})
        if ideal_blocks := q.get("ideal_answer"):
            # store the normalized ideal answer blocks as text for retrieval
            ideal_str = " ".join(b.get("content","") for b in ideal_blocks if isinstance(b, dict))
            if ideal_str.strip():
                vs_instance.add(f"{qid}-ideal", ideal_str, "text", {"type": "ideal", "q_id": qid})


# ============================== UI & LOGIC ====================================
st.set_page_config(page_title="Upload Data for Grading", layout="wide")
st.title("📄 Upload Assignment Data for Grading")

prof_pdf = st.file_uploader("📋 Lecturer PDF (use existing 'Professor' template)", type=["pdf"])
submission_file = st.file_uploader("📝 Student Submissions (PDF or ILIAS ZIP)", type=["pdf", "zip"])
language = st.selectbox("Grading Language", ["English", "German", "Spanish"])
st.session_state["answer_language"] = language

if st.button("🚦 Start Grading", disabled=not (prof_pdf and submission_file), type="primary"):
    # ---- Initialize Vector Store (if available) ----
    multimodal_vs_instance = None
    try:
        if 'multimodal_vs' not in st.session_state:
            with st.spinner("Initializing Multimodal Vector Store..."):
                st.session_state['multimodal_vs'] = MultimodalVectorStore()
        multimodal_vs_instance = st.session_state['multimodal_vs']
    except (IOError, ValueError) as e:
        st.warning(
            f"⚠️ Could not initialize embedding model: {e}. "
            "The RAG context retrieval feature will be disabled. Grading will proceed without it.",
            icon="⚠️"
        )
        st.session_state['multimodal_vs'] = None

    # ---- Professor PDF ----
    try:
        with st.spinner("Processing Lecturer PDF (expecting 'Professor' headings)..."):
            pdf_bytes = prof_pdf.getvalue()
            prof_content_blocks = extract_multimodal_content_from_pdf(BytesIO(pdf_bytes))
            prof_text = "\n".join([b['content'] for b in prof_content_blocks if b['type'] == 'text'])
            prof_info = parse_professor_pdf(prof_text)

            if not prof_info.get("questions"):
                st.error("Lecturer PDF missing Q1:, etc. (ensure the uploaded document keeps the original 'Professor' labels)")
                st.stop()

            # 🔧 normalize for UI + grader
            prof_info = _normalize_prof_info_for_ui_and_grader(prof_info)

            st.session_state["prof_data"] = prof_info

            if multimodal_vs_instance:
                seed_multimodal_rag_from_professor(prof_info, prof_content_blocks, multimodal_vs_instance)
                st.write("✅ Lecturer PDF processed and RAG seeded.")
            else:
                st.write("✅ Lecturer PDF processed (RAG feature disabled).")

    except Exception as e:
        st.error(f"❌ Error processing Lecturer PDF: {e}")
        st.stop()

    # ---- Student submissions (ZIP unchanged, single-PDF updated) ----
    students_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    errors: List[str] = []

    try:
        with st.spinner("Processing student submissions..."):
            if submission_file.name.lower().endswith(".zip"):
                # ZIP FLOW: UNCHANGED
                st.session_state["upload_type"] = "ilias_zip"
                ingest_result: IngestResult = parse_ilias_zip(
                    BytesIO(submission_file.getvalue()),
                    multimodal_extractor=extract_multimodal_content_from_pdf
                )
                st.session_state["ilias_ingest_result"] = ingest_result
                for student_folder in ingest_result.student_folders:
                    student_id = student_folder.email or student_folder.raw_folder
                    all_student_blocks = [block for f in student_folder.files for block in f.multimodal_content]
                    students_data[student_id] = process_student_data(all_student_blocks)
            else:
                # SINGLE PDF FLOW: handle multiple students in one file
                st.session_state["upload_type"] = "pdf"

                # 1) Extract raw text from the uploaded single PDF
                single_pdf_text = extract_text_from_pdf(BytesIO(submission_file.getvalue()))

                # 2) Split into students -> { "Student 1": {"A1":"...", ...}, "Student 2": {...}, ... }
                per_student_answers = parse_student_pdf(single_pdf_text)

                # 3) Convert each student's answers into the multimodal format expected by the grader
                #    e.g., { "A1": [ {type:"text", content:"..."} ], "A2": [...] }
                for student_label, answers in per_student_answers.items():
                    students_data[student_label] = {
                        akey: [{"type": "text", "content": atext}]
                        for akey, atext in answers.items()
                    }

        # ---- Validation: each student should have entries for every Qn ----
        qids = [q["id"] for q in st.session_state["prof_data"].get("questions", [])]
        for student_id, answers in students_data.items():
            for qid in qids:
                akey = qid.replace("Q", "A")
                if akey not in answers or not answers[akey]:
                    errors.append(f"**{student_id}** missing content for `{qid}` (`{akey}`).")

        if errors:
            st.error("❌ Validation failed:")
            st.write("\n".join(f"• {e}" for e in errors))
            st.stop()

        if not students_data:
            st.error("No student data extracted.")
            st.stop()

        st.session_state["students_data"] = students_data
        st.success(f"✅ Processed {len(students_data)} submissions. Redirecting...")
        st.switch_page("pages/2_grading_result.py")

    except Exception as e:
        st.error(f"❌ Error processing submissions: {e}")
        st.exception(e)
