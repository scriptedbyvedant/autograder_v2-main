from __future__ import annotations

import json
import os
import threading
import uuid
from typing import Any, Dict, List, Optional
from collections import defaultdict

import numpy as np

try:
    import faiss  # type: ignore
except Exception:
    faiss = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# ---------------------------------------------------------------------------
# Simple fallback store (in-memory token overlap)
# ---------------------------------------------------------------------------

class SimpleVectorStore:
    def __init__(self):
        self.items: List[Dict[str, Any]] = []
        self.by_q: Dict[str, List[int]] = defaultdict(list)

    def reset(self) -> None:
        self.items.clear()
        self.by_q.clear()

    def add(self, doc_id: str, text: str, meta: Dict[str, Any]) -> None:
        record = {"id": doc_id, "text": text or "", "meta": meta or {}}
        idx = len(self.items)
        self.items.append(record)
        qid = str(meta.get("q_id")) if meta and "q_id" in meta else None
        if qid:
            self.by_q[qid].append(idx)

    def get_by_q(self, q_id: str) -> List[Dict[str, Any]]:
        return [self.items[i] for i in self.by_q.get(str(q_id), [])]

    def search(self, query: str, k: int = 3, filter_q_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if filter_q_id:
            return self.get_by_q(filter_q_id)[:k]
        qset = set((query or "").lower().split())
        scored = []
        for it in self.items:
            tset = set(it["text"].lower().split())
            score = len(qset & tset)
            scored.append((score, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [hit for _, hit in scored[:k]]


# ---------------------------------------------------------------------------
# FAISS-backed store with persistence
# ---------------------------------------------------------------------------

class FaissVectorStore:
    def __init__(self, store_dir: str = "vector_store", model_name: str = "all-MiniLM-L6-v2"):
        if faiss is None or SentenceTransformer is None:
            raise RuntimeError("FAISS or SentenceTransformer not available")
        self._store_dir = store_dir
        self._index_path = os.path.join(store_dir, "rag_index.faiss")
        self._meta_path = os.path.join(store_dir, "rag_metadata.json")
        os.makedirs(store_dir, exist_ok=True)

        self._model = SentenceTransformer(model_name, device="cpu")
        self._dim = self._model.get_sentence_embedding_dimension()
        self._lock = threading.Lock()

        self.records: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []
        self.by_q: Dict[str, List[int]] = defaultdict(list)

        if os.path.exists(self._index_path):
            try:
                self.index = faiss.read_index(self._index_path)
                self._load_metadata()
            except Exception:
                self.index = faiss.IndexFlatIP(self._dim)
        else:
            self.index = faiss.IndexFlatIP(self._dim)

        if self.index.d != self._dim:
            # Reinitialize if dimension mismatch (e.g., different model)
            self.index = faiss.IndexFlatIP(self._dim)
            self.records.clear()
            self.doc_ids.clear()
            self.by_q.clear()
            self._save()

    def reset(self) -> None:
        with self._lock:
            self.index = faiss.IndexFlatIP(self._dim)
            self.records.clear()
            self.doc_ids.clear()
            self.by_q.clear()
            self._save()

    def add(self, doc_id: str, text: str, meta: Dict[str, Any]) -> None:
        if not text:
            return
        vector = self._embed(text)
        with self._lock:
            self.index.add(vector)
            record = {"id": doc_id, "text": text, "meta": meta or {}}
            idx = len(self.records)
            self.records.append(record)
            self.doc_ids.append(doc_id)
            qid = str(meta.get("q_id")) if meta and "q_id" in meta else None
            if qid:
                self.by_q[qid].append(idx)
            self._save()

    def get_by_q(self, q_id: str) -> List[Dict[str, Any]]:
        indices = self.by_q.get(str(q_id), [])
        return [self.records[i] for i in indices]

    def search(self, query: str, k: int = 5, filter_q_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.records:
                return []
            if filter_q_id:
                return [self.records[i] for i in self.by_q.get(str(filter_q_id), [])[:k]]
            if not query.strip():
                return self.records[:k]
            vector = self._embed(query)
            top_k = min(max(k * 2, k), len(self.records))
            scores, idxs = self.index.search(vector, top_k)
            hits: List[Dict[str, Any]] = []
            for score, idx in zip(scores[0], idxs[0]):
                if idx == -1:
                    continue
                record = dict(self.records[idx])
                record["score"] = float(score)
                hits.append(record)
            return hits[:k]

    def _embed(self, text: str) -> np.ndarray:
        emb = self._model.encode([text], normalize_embeddings=True)
        vec = np.asarray(emb, dtype="float32")
        return vec

    def _load_metadata(self) -> None:
        if not os.path.exists(self._meta_path):
            return
        with open(self._meta_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.records = data.get("records", [])
        self.doc_ids = data.get("doc_ids", [])
        self.by_q.clear()
        for idx, rec in enumerate(self.records):
            qid = str((rec.get("meta") or {}).get("q_id"))
            if qid and qid != "None":
                self.by_q.setdefault(qid, []).append(idx)

    def _save(self) -> None:
        faiss.write_index(self.index, self._index_path)
        payload = {"doc_ids": self.doc_ids, "records": self.records}
        with open(self._meta_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Store selection & helper functions
# ---------------------------------------------------------------------------

def _build_store() -> Any:
    try:
        return FaissVectorStore()
    except Exception:
        return SimpleVectorStore()


VS = _build_store()


def reset_vector_store() -> None:
    VS.reset()


def register_document(doc_id: str, text: str, meta: Dict[str, Any]) -> None:
    VS.add(doc_id, text, meta)


def add_correction_example(
    question_id: str,
    question_text: str,
    student_answer: str,
    feedback: str,
    editor_id: str
) -> None:
    if not question_id or not feedback.strip():
        return
    doc_text = (
        f"Question: {question_text or 'N/A'}\n"
        f"Student Answer: {student_answer or 'N/A'}\n"
        f"Instructor Feedback: {feedback.strip()}"
    )
    doc_id = f"{question_id}-correction-{uuid.uuid4().hex}"
    meta = {"q_id": question_id, "type": "correction", "source": "instructor_edit", "editor": editor_id}
    register_document(doc_id, doc_text, meta)


def retrieve_context(q_id: str, question: str, k: int = 3) -> Dict[str, Any]:
    """
    Pull rubric/ideal/exemplars for this question.
    """
    records = VS.get_by_q(q_id) if q_id else []
    rubric = next((rec for rec in records if (rec.get("meta") or {}).get("type") == "rubric"), None)
    ideal = next((rec for rec in records if (rec.get("meta") or {}).get("type") == "ideal"), None)
    exemplars = [rec for rec in records if (rec.get("meta") or {}).get("type") == "correction"]

    if not exemplars:
        search_hits = VS.search(question or "", k=k)
        exemplars = [rec for rec in search_hits if (rec.get("meta") or {}).get("type") == "correction"][:k]

    return {
        "rubric": rubric.get("text") if rubric else None,
        "ideal": ideal.get("text") if ideal else None,
        "exemplars": [{"text": rec.get("text"), "meta": rec.get("meta")} for rec in exemplars[:k]]
    }
