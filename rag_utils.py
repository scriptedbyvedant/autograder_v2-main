# rag_utils.py

from __future__ import annotations
from typing import Any, Dict, List
import json

try:
    import streamlit as st
except Exception:
    st = None  # type: ignore

# Import your store
from grader_engine.multimodal_rag import MultimodalVectorStore

def _to_blocks(obj) -> List[Dict[str, Any]]:
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
        return [{"type": obj.get("type") or obj.get("content_type") or "text", "content": obj.get("content", "")}]
    if isinstance(obj, str):
        return [{"type": "text", "content": obj}]
    return [{"type": "text", "content": str(obj)}]

def _blocks_to_text(blocks) -> str:
    return " ".join((b.get("content") or "") for b in _to_blocks(blocks)).strip()

def _ensure_vs() -> MultimodalVectorStore | None:
    """Return an existing vector store from session, or None if unavailable."""
    if st is None:
        return None
    vs = st.session_state.get("multimodal_vs")
    return vs if isinstance(vs, MultimodalVectorStore) else None

def seed_rag_from_professor(prof_info: Dict[str, Any]) -> None:
    """
    Seed the vector store with professor materials.
    Index per-question:
      - question text
      - ideal answer (flattened text)
      - rubric (as JSON string)
    Uses the signature: add(doc_id, text, content_type, meta)
    """
    vs = _ensure_vs()
    if vs is None:
        return

    # reset lightweight indices (keep API parity)
    try:
        vs.index.reset()
    except Exception:
        pass
    try:
        vs.items.clear()
        vs.by_q.clear()
    except Exception:
        pass

    questions = prof_info.get("questions", []) or []
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue

        qtext = (q.get("question") or "").strip()
        if qtext:
            vs.add(f"{qid}-question", qtext, "text", {"q_id": qid, "type": "question", "source": "professor"})

        # ideal_answer may already be blocks from the upload page normalization
        ideal_txt = _blocks_to_text(q.get("ideal_answer", [])) or (q.get("ideal_answer_text") or "")
        ideal_txt = ideal_txt.strip()
        if ideal_txt:
            vs.add(f"{qid}-ideal", ideal_txt, "text", {"q_id": qid, "type": "ideal", "source": "professor"})

        rubric = q.get("rubric") or []
        try:
            rub_str = json.dumps(rubric, ensure_ascii=False)
        except Exception:
            rub_str = str(rubric)
        if rub_str.strip():
            vs.add(f"{qid}-rubric", rub_str, "text", {"q_id": qid, "type": "rubric", "source": "professor"})
