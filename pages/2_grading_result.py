"""
Main Streamlit page for displaying grading results.
- Orchestrates RAG context retrieval and lazy-loaded grading.
- Manages UI state, editing, and feedback generation.
- Handles exporting results to PDF/ZIP.
- Adds RAG transparency (results + final context text).
"""

# --- Early, safe imports ---
import os
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch
if hasattr(torch, "set_default_device"):
    try:
        torch.set_default_device("cpu")
    except Exception:
        pass

import streamlit as st
st.set_page_config(page_title="⚖️ Grading Results", layout="wide")

import pandas as pd
import json, re, difflib, hashlib, io, zipfile, time, functools, importlib
from typing import List, Dict, Any, Tuple
from PIL import Image
import concurrent.futures

# --- App-specific imports ---
from database.postgres_handler import PostgresHandler
from grader_engine.multimodal_rag import retrieve_multimodal_context
from grader_engine.explainer import generate_explanation
from rag_utils import seed_rag_from_professor
from typing import Optional, Any

# --- Translations (UI strings) ---
TRANSLATIONS = {
    "English": {
        "page_title": "⚖️ Grading Results",
        "no_data": "Please upload data on the Upload page first.",
        "retrieving_context": "🔎 Retrieving context for all questions...",
        "grading_in_parallel": "🤖 Grading {task_count} answers in parallel...",
        "results_summary": "Results Summary",
        "detailed_view": "Detailed Grading & Editing",
        "question": "Question",
        "ideal_answer": "Ideal Answer",
        "student_answer": "Student Answer",
        "retrieved_context_title": "Retrieved Context (RAG)",
        "rag_results_header": "🔎 Search Results Found",
        "rag_final_context_header": "📄 Final Context Fed to LLM",
        "rag_blocks_header": "Context Blocks",
        "rag_text_header": "Raw Context Text",
        "rubric_breakdown": "🧮 Criteria Breakdown",
        "feedback": "📝 Feedback",
        "explain_button": "💡 Explanation",
        "save_changes": "💾 Save Changes",
        "no_answer": "No answer provided.",
        "debug_title": "🧪 Debug Info",
        "export_button": "📦 Download All Feedback",
        "share_expander": "🔗 Share Result With A Colleague",
        "share_email_input": "Enter colleague's email:",
        "share_button": "Share",
        "share_success": "Result shared successfully!",
        "share_error": "Failed to share the result.",
        "share_disabled_info": "Save this result before sharing it.",
        "invalid_email": "Please enter a valid email address.",
        "export_zip_label": "Download ZIP",
        "success_message_timed": "✅ All answers have been graded and saved in {elapsed_time:.2f} seconds!"
    },
    "German": {
        "page_title": "⚖️ Benotungsergebnisse",
        "no_data": "Bitte laden Sie zuerst Daten auf der Upload-Seite hoch.",
        "retrieving_context": "🔎 Kontext für alle Fragen wird abgerufen...",
        "grading_in_parallel": "🤖 Benote {task_count} Antworten parallel...",
        "results_summary": "Ergebnisübersicht",
        "detailed_view": "Detaillierte Benotung & Bearbeitung",
        "question": "Frage",
        "ideal_answer": "Ideale Antwort",
        "student_answer": "Antwort des Studierenden",
        "retrieved_context_title": "Abgerufener Kontext (RAG)",
        "rag_results_header": "🔎 Gefundene Suchergebnisse",
        "rag_final_context_header": "📄 Endgültiger Kontext ans LLM",
        "rag_blocks_header": "Kontextblöcke",
        "rag_text_header": "Rohtext des Kontexts",
        "rubric_breakdown": "🧮 Kriterienübersicht",
        "feedback": "📝 Feedback",
        "explain_button": "💡 Erklärung",
        "save_changes": "💾 Änderungen speichern",
        "no_answer": "Keine Antwort abgegeben.",
        "debug_title": "🧪 Debug-Info",
        "export_button": "📦 Alle Feedbacks herunterladen",
        "share_expander": "🔗 Ergebnis mit Kolleg:innen teilen",
        "share_email_input": "E-Mail-Adresse des Kollegen eingeben:",
        "share_button": "Teilen",
        "share_success": "Ergebnis erfolgreich geteilt!",
        "share_error": "Ergebnis konnte nicht geteilt werden.",
        "share_disabled_info": "Speichern Sie das Ergebnis, bevor Sie es teilen.",
        "invalid_email": "Bitte eine gültige E-Mail-Adresse eingeben.",
        "export_zip_label": "ZIP herunterladen",
        "success_message_timed": "✅ Alle Antworten wurden in {elapsed_time:.2f} Sekunden benotet und gespeichert!"
    },
    "Spanish": {
        "page_title": "⚖️ Resultados de Calificación", "question": "Pregunta", "ideal_answer": "Respuesta Ideal",
        "student_answer": "Respuesta del Estudiante", "rubric_breakdown": "🧮 Desglose de Criterios",
        "feedback": "📝 Comentarios", "save_changes": "💾 Guardar Cambios", "results_summary": "Resumen de Resultados",
        "detailed_view": "Calificación y Edición Detallada",
        "no_data": "Por favor, suba los datos en la página de Carga primero.", "no_answer": "No se proporcionó respuesta.",
        "debug_title": "🧪 Depuración del LLM", "retrieved_context_title": "Contexto Recuperado",
        "export_button": "📦 Descargar Todos los Comentarios", "share_expander": "🔗 Compartir Resultado con un Colega",
        "share_email_input": "Ingrese el correo electrónico del colega:", "share_button": "Compartir",
        "share_success": "¡Resultado compartido con éxito!", "share_error": "Error al compartir el resultado.",
        "share_disabled_info": "Guarde este resultado antes de compartirlo.",
        "invalid_email": "Por favor, ingrese una dirección de correo electrónico válida.",
        "code_feedback_tests": "{passed} de {total} casos de prueba superados.",
        "code_feedback_failures_header": "\n**Pruebas Fallidas:**",
        "code_feedback_failure_item": "- Entrada: `{input}`\n  - Esperado: `{expected}`\n  - Obtenido: `{got}`",
        "code_feedback_blank": "La entrega estaba vacía.",
        "code_feedback_invalid": "La entrega no era código Python válido y no pudo ser ejecutada.",
        "code_feedback_runtime_error": "El código era sintácticamente correcto pero falló al ejecutarse. Error: `{error}`",
        "code_feedback_generic_fail": "La evaluación del código falló. Razón: {reason}"
    },
    "French": {
        "page_title": "⚖️ Résultats de notation", "question": "Question", "ideal_answer": "Réponse idéale",
        "student_answer": "Réponse de l'étudiant", "rubric_breakdown": "🧮 Détail des critères",
        "feedback": "📝 Commentaires", "save_changes": "💾 Enregistrer les modifications", "results_summary": "Résumé des résultats",
        "detailed_view": "Notation et édition détaillées",
        "no_data": "Veuillez d'abord télécharger les données sur la page de téléchargement.", "no_answer": "Aucune réponse fournie.",
        "debug_title": "🧪 Débogage du LLM", "retrieved_context_title": "Contexte récupéré",
        "export_button": "📦 Télécharger tous les commentaires", "share_expander": "🔗 Partager le résultat avec un collègue",
        "share_email_input": "Entrez l'adresse e-mail du collègue :", "share_button": "Partager",
        "share_success": "Résultat partagé avec succès !", "share_error": "Échec du partage du résultat.",
        "share_disabled_info": "Enregistrez ce résultat avant de le partager.",
        "invalid_email": "Veuillez saisir une adresse e-mail valide.",
        "code_feedback_tests": "{passed} des {total} cas de test réussis.",
        "code_feedback_failures_header": "\n**Tests échoués :**",
        "code_feedback_failure_item": "- Entrée : `{input}`\n  - Attendu : `{expected}`\n  - Reçu : `{got}`",
        "code_feedback_blank": "La soumission était vide.",
        "code_feedback_invalid": "La soumission n'était pas un code Python valide et n'a pas pu être exécutée.",
        "code_feedback_runtime_error": "Le code était syntaxiquement correct mais n'a pas pu s'exécuter. Erreur : `{error}`",
        "code_feedback_generic_fail": "L'évaluation du code a échoué. Raison : {reason}"
    },
    "Hindi": {
        "page_title": "⚖️ ग्रेडिंग परिणाम", "question": "प्रश्न", "ideal_answer": "आदर्श उत्तर",
        "student_answer": "छात्र का उत्तर", "rubric_breakdown": "🧮 मानदंड विवरण",
        "feedback": "📝 प्रतिक्रिया", "save_changes": "💾 परिवर्तन सहेजें", "results_summary": "परिणाम सारांश",
        "detailed_view": "विस्तृत ग्रेडिंग और संपादन",
        "no_data": "कृपया पहले अपलोड पेज पर डेटा अपलोड करें।", "no_answer": "कोई उत्तर नहीं दिया गया।",
        "debug_title": "🧪 एलएलएम डीबग", "retrieved_context_title": "पुनर्प्राप्त संदर्भ",
        "export_button": "📦 सभी फीडबैक डाउनलोड करें", "share_expander": "🔗 किसी सहकर्मी के साथ परिणाम साझा करें",
        "share_email_input": "सहकर्मी का ईमेल पता दर्ज करें:", "share_button": "साझा करें",
        "share_success": "परिणाम सफलतापूर्वक साझा किया गया!", "share_error": "परिणाम साझा करने में विफल।",
        "share_disabled_info": "इसे साझा करने से पहले परिणाम सहेजें।",
        "invalid_email": "कृपया एक वैध ईमेल पता दर्ज करें।",
        "code_feedback_tests": "{total} में से {passed} टेस्ट केस पास हुए।",
        "code_feedback_failures_header": "\n**असफल टेस्ट:**",
        "code_feedback_failure_item": "- इनपुट: `{input}`\n  - अपेक्षित: `{expected}`\n  - मिला: `{got}`",
        "code_feedback_blank": "सबमिशन खाली था।",
        "code_feedback_invalid": "सबमिशन मान्य पायथन कोड नहीं था और निष्पादित नहीं किया जा सका।",
        "code_feedback_runtime_error": "कोड वाक्यात्मक रूप से सही था लेकिन चलने में विफल रहा। त्रुटि: `{error}`",
        "code_feedback_generic_fail": "कोड मूल्यांकन विफल रहा। कारण: {reason}"
    }
}

# ---- Normalizers & helpers ---------------------------------------------------
def _to_blocks(obj) -> List[Dict[str, Any]]:
    """Coerce str|dict|list into a list of block dicts: [{'type':'text','content':...}, ...]."""
    if obj is None:
        return []
    if isinstance(obj, list):
        out = []
        for it in obj:
            if isinstance(it, dict):
                if "type" in it and "content" in it:
                    out.append(it)
                elif "content" in it:
                    out.append({"type": it.get("type") or it.get("content_type") or "text", "content": it["content"]})
                else:
                    out.append({"type": "text", "content": json.dumps(it, ensure_ascii=False)})
            elif isinstance(it, str):
                out.append({"type": "text", "content": it})
            else:
                out.append({"type": "text", "content": str(it)})
        return out
    if isinstance(obj, dict):
        if "type" in obj and "content" in obj:
            return [obj]
        return [{"type": obj.get("type") or obj.get("content_type") or "text", "content": obj.get("content","")}]
    if isinstance(obj, str):
        return [{"type": "text", "content": obj}]
    return [{"type": "text", "content": str(obj)}]

def _blocks_to_plain_text(blocks) -> str:
    blocks = _to_blocks(blocks)
    return " ".join((b.get("content") or "") for b in blocks if isinstance(b, dict)).strip()

def render_content_blocks(title: str, content_blocks):
    """Tolerant renderer: accepts str | dict | list[dict|str]."""
    st.markdown(f"**{title}**")
    blocks = _to_blocks(content_blocks)
    if not blocks:
        st.info("No content provided for this section.")
        return
    for item in blocks:
        content_type = (item.get('type') or item.get('content_type') or "text")
        content = item.get('content')
        if content_type in (None, "text"):
            st.write(content or "")
        elif content_type == "image":
            try:
                st.image(content, use_container_width=True)
            except Exception:
                st.code(f"[image] {str(content)[:120]}")
        elif content_type == "code":
            st.code(content or "", language=item.get("lang") or item.get("language"))
        else:
            st.code(json.dumps(item, ensure_ascii=False, indent=2))

def _make_serializable(obj):
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)

def _dedupe_feedback(text: str) -> str:
    if not text:
        return text
    lines, seen, out = text.splitlines(), set(), []
    for ln in lines:
        key = ln.strip().lower()
        if key and key not in seen:
            out.append(ln)
            seen.add(key)
    return "\n".join(out)

def _is_valid_email(value: str) -> bool:
    if not value:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))

def _total_possible(rubric_list: List[Dict[str, Any]]) -> int:
    return sum(int(r.get("points", 0)) for r in rubric_list or [])

def _signature(prof_data: Dict, students_data: Dict, language: str) -> str:
    payload = json.dumps(
        {"prof": prof_data, "students": _make_serializable(students_data), "lang": language},
        sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def update_score_callback(student, q_id, rubric_idx, slider_key):
    if slider_key in st.session_state:
        st.session_state["grading_cache"]['results'][f"{student}_{q_id}"]['rubric_scores'][rubric_idx]['score'] = st.session_state[slider_key]

def _normalize_rag_results(raw_results) -> List[Dict[str, Any]]:
    """Normalize potential RAG result formats into {title, source, url, page, score, snippet}."""
    norm = []
    if not raw_results:
        return norm
    for item in raw_results:
        title = item.get("title") or item.get("document_title") or item.get("name") or ""
        source = item.get("source") or item.get("collection") or item.get("dataset") or item.get("origin") or ""
        url = item.get("url") or item.get("link") or item.get("href") or ""
        page = item.get("page") or item.get("page_number") or item.get("pageno") or None
        score = item.get("score") or item.get("_score") or item.get("similarity") or item.get("relevance") or None
        snippet = item.get("snippet") or item.get("preview") or item.get("text") or item.get("content") or item.get("chunk") or ""
        try:
            page_val = int(page) if page is not None and str(page).isdigit() else page
        except Exception:
            page_val = page
        try:
            score_val = float(score) if isinstance(score, (int, float)) or str(score).replace('.', '', 1).isdigit() else score
        except Exception:
            score_val = score
        norm.append({
            "title": str(title)[:200],
            "source": str(source)[:120],
            "url": str(url)[:300],
            "page": page_val,
            "score": score_val,
            "snippet": str(snippet)[:600]
        })
    return norm

# ---------------- Grading task (single answer) ----------------
def grade_single_answer_task(student_id: str, q: Dict, student_answers: Dict, language: str, T: Dict, rag_context_map: Dict):
    """
    Grades one answer, dispatching to code or text grader.
    RAG context is passed in; text_grader is lazy-loaded inside.
    """
    key = f"{student_id}_{q['id']}"

    # ✅ Map Q# -> A# for lookup (was causing all zeros before)
    ans_key = q["id"].replace("Q", "A", 1)
    stud_ans_content = student_answers.get(ans_key, [])

    # Normalize ideal answer for both UI (blocks) and grader (plain string)
    ideal_blocks = _to_blocks(q.get("ideal_answer", []))
    ideal_text = _blocks_to_plain_text(ideal_blocks)

    rubric_list = q.get("rubric", [])

    aligned = [{"criteria": r.get("criteria","Criteria"), "score": 0} for r in rubric_list]
    feedback_txt, llm_debug, ctx_items = T["no_answer"], {}, []

    is_code_question = "tests" in q or any(
        kw in (q.get('question','') or '').lower() for kw in ['python', 'program', 'code', 'function']
    )

    # RAG transparency placeholders
    rag_results_tbl = []
    rag_context_text = ""

    if not stud_ans_content:
        pass
    elif is_code_question:
        code_mod = importlib.import_module("grader_engine.code_grader")
        grade_code = getattr(code_mod, "grade_code")

        student_code = next((b.get('content', '') for b in _to_blocks(stud_ans_content) if b.get('type') == 'text'), '')
        tests = q.get('tests', [])
        total_award, rubric_breakdown, details = grade_code(
            student_code=student_code, tests=tests, rubric=rubric_list
        )
        aligned = rubric_breakdown
        reason = details.get("reason", "N/A")
        if reason == "tests":
            passed = details.get("passed", 0)
            total = details.get("total", 0)
            fails = details.get("failures", [])
            parts = [f"Passed {passed} of {total} test cases."]
            if fails:
                parts.append("\n**Failed Tests:**")
                for failure in fails[:3]:
                    parts.append(f"- Input: `{failure.get('input','')}`\n  - Expected: `{failure.get('expected','')}`\n  - Got: `{failure.get('got','')}`")
            feedback_txt = "\n".join(parts)
        elif reason == "blank":
            feedback_txt = "The submission was empty."
        elif reason == "no_tests_and_bad_code":
            feedback_txt = "The submission was not valid Python code and could not be executed."
        elif "syntax_ok" in reason:
            feedback_txt = f"The code was syntactically correct but failed to run. Error: `{details.get('stderr','Unknown issue')}`"
        else:
            feedback_txt = f"Code evaluation failed. Reason: {reason}"
        llm_debug = {"grader": "code_grader", "details": details}
    else:
        # Text question path (multimodal RAG + LLM)
        rag_result = rag_context_map.get(q['id'], {}) or {}
        raw_results = rag_result.get("results") or rag_result.get("hits") or rag_result.get("documents") or []
        rag_results_tbl = _normalize_rag_results(raw_results)
        ctx_items = rag_result.get("context", []) or []
        rag_context_text = (
            rag_result.get("context_text")
            or " ".join(
                b.get("content", "") for b in ctx_items
                if isinstance(b, dict) and b.get("type") in (None, "text")
            ).strip()
        )

        text_mod = importlib.import_module("grader_engine.multimodal_grader")
        grade_answer_multimodal = getattr(text_mod, "grade_answer_multimodal")

        out = grade_answer_multimodal(
            question=q.get('question', ''),
            ideal_answer=ideal_text,                 # ✅ pass plain text to grader
            rubric=rubric_list,
            student_answer_blocks=_to_blocks(stud_ans_content),
            multimodal_context=ctx_items,
            language=language,
            return_debug=True
        )
        existing = {r.get("criteria","Criteria"): r.get("score", 0) for r in (out.get("rubric_scores") or [])}
        aligned = [{"criteria": r.get("criteria","Criteria"), "score": int(existing.get(r.get("criteria","Criteria"), 0))} for r in rubric_list]
        feedback_txt = _dedupe_feedback(out.get("feedback", T["no_answer"]))
        llm_debug = out.get("debug", {})
        llm_debug["rag_result"] = _make_serializable(rag_result)

    result_data = {
        "student_id": student_id,
        "question": q.get("question",""),
        "ideal_answer": ideal_blocks,              # ✅ store normalized blocks for UI
        "student_answer_content": _to_blocks(stud_ans_content),
        "rubric_list": rubric_list,
        "rubric_scores": [
            {"criteria": a["criteria"], "score": int(a.get("score", 0)), "original_score": int(a.get("score", 0))}
            for a in aligned
        ],
        "feedback": {"text": feedback_txt, "original": feedback_txt},
        "llm_debug": llm_debug,
        "multimodal_context_items": ctx_items,
        # RAG transparency:
        "rag_results": rag_results_tbl,
        "rag_context_text": rag_context_text
    }
    return key, result_data

# ---------------- Main Page ----------------
def grading_result_page():
    if "logged_in_prof" not in st.session_state: st.warning("Please login first."); st.stop()
    prof = st.session_state["logged_in_prof"]; my_email = prof.get("university_email","")
    try: db = PostgresHandler()
    except Exception as e: st.error(f"Database connection failed: {e}"); st.stop()

    prof_data = st.session_state.get("prof_data")
    students_data = st.session_state.get("students_data")
    language = st.session_state.get("answer_language", "English")
    T = TRANSLATIONS.get(language, TRANSLATIONS["English"])
    if not prof_data or not students_data: st.warning(T["no_data"]); return

    st.title(T["page_title"])
    seed_rag_from_professor(prof_data)

    sig = _signature(prof_data, students_data, language)
    if st.session_state.get("grading_cache", {}).get("signature") != sig:
        start_time = time.time()
        grading_results = {}
        tasks = [(sid, q, ans) for sid, ans in students_data.items() for q in prof_data["questions"]]
        progress_bar = st.progress(0, text="Starting...")

        rag_context_map = {}
        with st.spinner(T["retrieving_context"]):
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_q = {executor.submit(retrieve_multimodal_context, q_id=q['id'], question=q['question']): q for q in prof_data["questions"]}
                for future in concurrent.futures.as_completed(future_to_q):
                    q = future_to_q[future]
                    try: rag_context_map[q['id']] = future.result()
                    except Exception as e:
                        st.error(f"Vector search failed for q_id={q['id']}. Error: {e}")
                        rag_context_map[q['id']] = {}

        tasks_done = 0
        with st.spinner(T["grading_in_parallel"].format(task_count=len(tasks))):
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                future_to_task = {executor.submit(grade_single_answer_task, sid, q, ans, language, T, rag_context_map): (sid, q) for sid, q, ans in tasks}
                for future in concurrent.futures.as_completed(future_to_task):
                    try:
                        key, result_data = future.result()
                        grading_results[key] = result_data
                        tasks_done += 1
                        progress_bar.progress(int(100 * tasks_done / max(1, len(tasks))), text=f"Graded {tasks_done}/{len(tasks)}")
                    except Exception as exc:
                        sid, q = future_to_task[future]
                        st.error(f"Error grading Q {q['id']} for {sid}: {exc}")

        for key, result in grading_results.items():
            total_score = sum(s['score'] for s in result['rubric_scores'])
            student_answer_str = json.dumps(_make_serializable(result['student_answer_content']))
            db_id = db.insert_or_update_grading_result(
                student_id=result['student_id'], professor_id=my_email, course=prof_data.get("course", ""),
                semester=prof_data.get("session", ""), assignment_no=prof_data.get("assignment_no", ""),
                question=result["question"], student_answer=student_answer_str, language=language,
                old_score=total_score, new_score=total_score, old_feedback=result["feedback"]["text"], new_feedback=result["feedback"]["text"])
            result['db_id'] = db_id

        st.session_state["grading_cache"] = {"signature": sig, "results": grading_results}
        progress_bar.empty()
        st.success(T["success_message_timed"].format(elapsed_time=time.time() - start_time))

    grading_results = st.session_state["grading_cache"]['results']

    st.subheader(T["results_summary"])
    rows = []
    for student in students_data:
        tot_sc = tot_ps = 0
        row = {"Student": student}
        for q in prof_data["questions"]:
            k = f"{student}_{q['id']}"
            if k in grading_results:
                sc = sum(int(it["score"]) for it in grading_results[k]["rubric_scores"])
                ps = _total_possible(q.get("rubric",[]))
                row[q["id"]] = f"{sc}/{ps}"
                tot_sc += sc
                tot_ps += ps
        row["Total"] = f"{tot_sc}/{tot_ps}"
        rows.append(row)
    if rows: st.table(pd.DataFrame(rows).set_index("Student"))

    st.subheader(T["detailed_view"])
    sel_st = st.selectbox("Select Student", list(students_data.keys()))
    sel_q_options = [q['id'] for q in prof_data["questions"]]
    if not sel_q_options: st.warning("No questions found."); st.stop()
    sel_q = st.selectbox("Select Question", sel_q_options)
    detail_key = f"{sel_st}_{sel_q}"

    if detail_key not in grading_results: st.error("Could not find grading data for this selection."); st.stop()
    stored = grading_results[detail_key]

    st.markdown(f"**{T['question']}:** {next(q['question'] for q in prof_data['questions'] if q['id']==sel_q)}")

    col1, col2 = st.columns(2)
    with col1: render_content_blocks(T['ideal_answer'], stored.get('ideal_answer', []))
    with col2: render_content_blocks(T['student_answer'], stored.get('student_answer_content', []))

    # --------- RAG TRANSPARENCY UI ----------
    #with st.expander(T["retrieved_context_title"], expanded=False):
        #st.markdown(f"### {T.get('rag_results_header')}")
        #rag_results_tbl = stored.get("rag_results", [])
        #if rag_results_tbl:
         #   tbl = []
          #  for r in rag_results_tbl:
           #     url = r.get("url", "")
            #    link = f"[link]({url})" if url else ""
             #   tbl.append({
              #      "Source": r.get("source", ""),
               #     "Title": r.get("title", ""),
                #    "Score": r.get("score", ""),
                 #   "Page": r.get("page", ""),
                  #  "Snippet": r.get("snippet", ""),
                   # "URL": link
                #})
            #st.dataframe(tbl, use_container_width=True)
        #else:
         #   st.info("No explicit search results returned by RAG.")

        #st.markdown(f"### {T.get('rag_final_context_header')}")
        #cxa, cxb = st.columns(2)
        #with cxa:
         #   st.markdown(f"**{T.get('rag_blocks_header')}**")
          #  for block in stored.get("multimodal_context_items", []):
           #     btype = block.get('type')
            #    if btype == 'text':
             #       st.write(block.get('content', ''))
              #  elif btype == 'image':
               #     st.image(block.get('content', ''), use_container_width=True)
                #else:
                 #   st.code(json.dumps(block, ensure_ascii=False, indent=2))
        #with cxb:
         #   st.markdown(f"**{T.get('rag_text_header')}**")
          #  st.text_area("context_text", value=stored.get("rag_context_text", ""), height=250, label_visibility="collapsed")
    # --------- END RAG TRANSPARENCY UI ----------

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(T["rubric_breakdown"])
        for idx, crit in enumerate(stored["rubric_list"]):
            init_score = int(stored["rubric_scores"][idx]["score"])
            max_pts = int(crit.get("points", 0)); slider_key = f"slider_{detail_key}_{idx}"
            st.slider(f'{crit["criteria"]} (Points: {max_pts})', min_value=0, max_value=max_pts, value=init_score, key=slider_key, on_change=update_score_callback, args=(sel_st, sel_q, idx, slider_key))
        total_now = sum(int(x["score"]) for x in stored["rubric_scores"])
        st.info(f"**Total Score: {total_now} / {_total_possible(stored['rubric_list'])}**")

    with c2:
        st.markdown(T["feedback"])
        fb_key = f"fb_{detail_key}"
        fb_text = st.text_area("Feedback", value=stored["feedback"]["text"], key=fb_key, height=300, label_visibility="collapsed")
        stored["feedback"]["text"] = _dedupe_feedback(fb_text)

    # 💡 Explanation button
    if st.button(T.get("explain_button", "💡 Explanation"), key=f"explain_{detail_key}"):
        assigned_score = sum(int(item["score"]) for item in stored.get("rubric_scores", []))
        student_answer_text = _blocks_to_plain_text(stored.get("student_answer_content", []))
        with st.spinner("Generating explanation..."):
            explanation = generate_explanation(
                question=stored.get("question", next(q['question'] for q in prof_data['questions'] if q['id']==sel_q)),
                ideal_answer=_blocks_to_plain_text(stored.get("ideal_answer", [])),
                rubric=stored.get("rubric_list", []),
                student_answer=student_answer_text,
                assigned_score=assigned_score,
                language=language
            )
        st.subheader(T.get("explain_button", "💡 Explanation"))
        st.text_area("Detailed Explanation", explanation, height=200, key=f"exp_{detail_key}")

    if st.button(T["save_changes"], key=f"save_{detail_key}", type="primary"):
        new_total_score = sum(item["score"] for item in stored["rubric_scores"])
        db.update_grading_result_with_correction(grading_result_id=stored["db_id"], new_score=float(new_total_score), new_feedback=stored["feedback"]["text"], editor_id=my_email)
        stored["feedback"]["original"] = stored["feedback"]["text"]
        for item in stored["rubric_scores"]: item["original_score"] = item["score"]
        st.success("✅ Changes saved!")

    with st.expander(T.get("share_expander", "Share with a colleague")):
        share_email_key = f"share_email_{detail_key}"
        share_email = st.text_input(T.get("share_email_input", "Colleague email:"), key=share_email_key)
        share_button_disabled = stored.get("db_id") is None
        if share_button_disabled:
            st.info(T.get("share_disabled_info", "Save this result before sharing it."))
        if st.button(T.get("share_button", "Share"), key=f"share_btn_{detail_key}", disabled=share_button_disabled):
            if not _is_valid_email(share_email):
                st.warning(T.get("invalid_email", "Please provide a valid email address."))
            else:
                try:
                    db.share_result(owner_email=my_email, target_email=share_email, result_id=stored["db_id"])
                    st.success(T.get("share_success", "Result shared successfully!"))
                    share_email = ""
                except Exception as exc:
                    st.error(f"{T.get('share_error', 'Failed to share the result.')} ({exc})")

    # Debug expander
    with st.expander(T["debug_title"]):
        st.json(stored.get("llm_debug", {}))

        # Export all feedback as ZIP of PDFs
    st.markdown("---")
    st.subheader("Download Feedback")

    pdf_mod = importlib.import_module("ilias_utils.pdf_feedback")
    FeedbackPDFGenerator = getattr(pdf_mod, "FeedbackPDFGenerator")
    
     
    
    ilias_ingest: Optional[Any] = st.session_state.get("ilias_ingest_result")
    assignment_name = (ilias_ingest.assignment_name if ilias_ingest else prof_data.get("assignment_no", "feedback")) or "feedback"

    if st.button(T["export_button"], type="primary"):
        with st.spinner("Generating PDF feedback for all students..."):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for student_id in students_data.keys():
                    student_grading_data = []
                    student_total_score = 0
                    student_total_possible = 0

                    for q in prof_data.get("questions", []):
                        key = f"{student_id}_{q['id']}"
                        if key not in grading_results: continue
                        
                        result = grading_results[key]
                        student_grading_data.append(result)
                        
                        student_total_score += sum(r.get("score", 0) for r in result.get("rubric_scores", []))
                        student_total_possible += _total_possible(q.get("rubric", []))

                    pdf_bytes_io = FeedbackPDFGenerator.create_pdf(
                        student_id=student_id,
                        assignment_name=assignment_name,
                        grading_data=student_grading_data,
                        total_score=student_total_score,
                        total_possible=student_total_possible
                    )
                    
                    safe_student_id = re.sub(r'[^a-zA-Z0-9_.-]', '_', student_id)
                    file_path_in_zip = f"{safe_student_id}/feedback_report.pdf"
                    zip_file.writestr(file_path_in_zip, pdf_bytes_io.getvalue())

            st.session_state["feedback_zip_buffer"] = zip_buffer.getvalue()
            st.success("Generated feedback zip with PDF reports.")

    if "feedback_zip_buffer" in st.session_state:
        st.download_button(
            label=T["export_zip_label"],
            data=st.session_state["feedback_zip_buffer"],
            file_name=f"{re.sub(r'[^a-zA-Z0-9_.-]', '_', assignment_name)}_feedback.zip",
            mime="application/zip",
            on_click=lambda: st.session_state.pop("feedback_zip_buffer", None)
        )

if __name__ == "__main__":
    grading_result_page()
