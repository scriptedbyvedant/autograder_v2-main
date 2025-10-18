# grader_engine/multimodal_rag.py
# Safe, fallback-ready multimodal RAG utilities

from __future__ import annotations
import os
import json
from typing import Any, Dict, List, Optional, Tuple
import logging

# Streamlit is optional here; we guard imports.
try:
    import streamlit as st
except Exception:
    st = None  # type: ignore

_LOG = logging.getLogger(__name__)
_LOG.setLevel(logging.INFO)

# ---------------- Embedding backends (tiered) ----------------
_BACKEND_ST = "sentence-transformers"
_BACKEND_TFIDF = "tfidf"
_BACKEND_NOOP = "noop"


def _try_load_st_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Try to load SentenceTransformer on CPU.
    Return (model, backend_name). On failure, return (None, None).
    """
    try:
        from sentence_transformers import SentenceTransformer
        # force CPU; avoids CUDA/MPS meta-tensor issues in some envs
        model = SentenceTransformer(model_name, device="cpu")
        _LOG.info("Loaded SentenceTransformer '%s' on CPU.", model_name)
        return model, _BACKEND_ST
    except Exception as e:
        _LOG.warning("SentenceTransformer load failed: %s", e)
        return None, None


def _try_load_tfidf():
    """
    Try to load scikit-learn TF-IDF fallback.
    Return (vectorizer_class, cosine_fn, backend_name) or (None, None, None) on failure.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        def cos(a, b):
            return cosine_similarity(a, b)

        _LOG.info("Using TF-IDF fallback backend.")
        return TfidfVectorizer, cos, _BACKEND_TFIDF
    except Exception as e:
        _LOG.warning("TF-IDF fallback not available: %s", e)
        return None, None, None


# ---------------- Vector Store ----------------
class MultimodalVectorStore:
    """
    Safe vector store with tiered backends:
      1) SentenceTransformers (CPU)
      2) TF-IDF cosine fallback
      3) No-op (always returns empty results)
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.items: List[Dict[str, Any]] = []   # [{id, text, type, meta}]
        self.by_q: Dict[str, List[int]] = {}    # q_id -> indices into items
        self.index = _DummyIndex()               # used only to keep API compatibility

        self.backend = _BACKEND_NOOP
        self._st_model = None
        self._tfidf_vec = None
        self._tfidf_matrix = None
        self._tfidf_cls = None
        self._cos_fn = None
        self._model_name = model_name

        # Try ST first
        st_model, backend = _try_load_st_model(model_name)
        if st_model is not None:
            self._st_model = st_model
            self.backend = backend
            return

        # Try TF-IDF fallback
        vec_cls, cos_fn, backend = _try_load_tfidf()
        if vec_cls is not None:
            self._tfidf_cls = vec_cls
            self._cos_fn = cos_fn
            self.backend = backend
            return

        # No-op fallback
        self.backend = _BACKEND_NOOP
        _LOG.warning("All embedding backends unavailable. RAG will be disabled.")

    # ------------- Public API -------------
    def add(self, doc_id: str, text: str, content_type: str, meta: Optional[Dict[str, Any]] = None) -> None:
        meta = meta or {}
        rec = {"id": doc_id, "text": text or "", "type": content_type, "meta": meta}
        idx = len(self.items)
        self.items.append(rec)
        if "q_id" in meta:
            self.by_q.setdefault(str(meta["q_id"]), []).append(idx)

        # Update TF-IDF matrix lazily if using that backend
        if self.backend == _BACKEND_TFIDF and self._tfidf_cls is not None:
            texts = [it["text"] for it in self.items]
            try:
                if self._tfidf_vec is None:
                    self._tfidf_vec = self._tfidf_cls(stop_words="english")
                    self._tfidf_matrix = self._tfidf_vec.fit_transform(texts)
                else:
                    # Refit on all texts to keep it simple (small corpora typical here)
                    self._tfidf_matrix = self._tfidf_vec.fit_transform(texts)
            except Exception as e:
                _LOG.warning("TF-IDF update failed: %s", e)
                self._tfidf_vec = None
                self._tfidf_matrix = None

    def search(self, query: str, top_k: int = 5, filter_q_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not query:
            return []

        if self.backend == _BACKEND_ST and self._st_model is not None:
            return self._search_st(query, top_k, filter_q_id)

        if self.backend == _BACKEND_TFIDF and self._tfidf_vec is not None and self._tfidf_matrix is not None:
            return self._search_tfidf(query, top_k, filter_q_id)

        # NOOP
        return []

    # ------------- Internal search impls -------------
    def _filtered_indices(self, filter_q_id: Optional[str]) -> List[int]:
        if filter_q_id and filter_q_id in self.by_q:
            return self.by_q[filter_q_id]
        return list(range(len(self.items)))

    def _search_st(self, query: str, top_k: int, filter_q_id: Optional[str]) -> List[Dict[str, Any]]:
        try:
            cand_idx = self._filtered_indices(filter_q_id)
            if not cand_idx:
                return []
            texts = [self.items[i]["text"] for i in cand_idx]
            q_emb = self._st_model.encode([query], convert_to_tensor=True, device="cpu", normalize_embeddings=True)
            c_emb = self._st_model.encode(texts, convert_to_tensor=True, device="cpu", normalize_embeddings=True)
            # cosine similarity
            import torch
            sims = (q_emb @ c_emb.T).squeeze(0)  # shape [N]
            topk = torch.topk(sims, k=min(top_k, sims.shape[0]))
            results: List[Dict[str, Any]] = []
            for score, pos in zip(topk.values.tolist(), topk.indices.tolist()):
                idx = cand_idx[pos]
                it = self.items[idx]
                results.append({
                    "score": float(score),
                    "text": it["text"],
                    "type": it["type"],
                    "meta": it["meta"],
                    "document_title": it["meta"].get("source", ""),
                    "page": it["meta"].get("page", None),
                    "url": it["meta"].get("url", "")
                })
            return results
        except Exception as e:
            _LOG.warning("ST search failed: %s", e)
            return []

    def _search_tfidf(self, query: str, top_k: int, filter_q_id: Optional[str]) -> List[Dict[str, Any]]:
        try:
            cand_idx = self._filtered_indices(filter_q_id)
            if not cand_idx:
                return []
            texts = [self.items[i]["text"] for i in cand_idx]
            q_vec = self._tfidf_vec.transform([query])
            # Recompute matrix for candidates only to get scores aligned
            from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
            # Note: For simplicity, reuse the full matrix and then slice — consistent fit above.
            import numpy as np
            sims = self._cos_fn(self._tfidf_matrix[cand_idx], q_vec).reshape(-1)
            order = np.argsort(-sims)[:min(top_k, len(sims))]
            results: List[Dict[str, Any]] = []
            for pos in order:
                score = float(sims[pos])
                idx = cand_idx[int(pos)]
                it = self.items[idx]
                results.append({
                    "score": score,
                    "text": it["text"],
                    "type": it["type"],
                    "meta": it["meta"],
                    "document_title": it["meta"].get("source", ""),
                    "page": it["meta"].get("page", None),
                    "url": it["meta"].get("url", "")
                })
            return results
        except Exception as e:
            _LOG.warning("TF-IDF search failed: %s", e)
            return []


class _DummyIndex:
    """Placeholder to keep .index.reset() calls harmless."""
    def reset(self) -> None:
        return


# ---------------- Public retrieval API ----------------
def retrieve_multimodal_context(q_id: str, question: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Return a dict shaped like:
    {
      "results": [ {title, source, url, page, score, snippet?}, ... ],
      "context": [ {"type":"text","content": "...", "meta": {...}}, ... ],
      "context_text": "...",
    }
    This function is SAFE: if the vector store isn’t available, it returns an empty payload.
    """
    try:
        vs = None
        if st is not None:
            vs = st.session_state.get("multimodal_vs")
        if vs is None or not isinstance(vs, MultimodalVectorStore):
            return {"results": [], "context": [], "context_text": ""}

        hits = vs.search(query=question, top_k=top_k, filter_q_id=str(q_id))
        # Turn hits into context blocks (text only here)
        blocks = [{"type": "text", "content": h.get("text",""), "meta": h.get("meta", {})} for h in hits if h.get("text")]
        ctx_text = " ".join(b["content"] for b in blocks).strip()
        # Normalize results table
        results_tbl = []
        for h in hits:
            results_tbl.append({
                "title": h.get("document_title",""),
                "source": h.get("meta",{}).get("source","") if isinstance(h.get("meta"), dict) else "",
                "url": h.get("url",""),
                "page": h.get("page", None),
                "score": h.get("score", None),
                "snippet": (h.get("text","")[:300] + "…") if h.get("text") and len(h["text"]) > 300 else h.get("text","")
            })
        return {
            "results": results_tbl,
            "context": blocks,
            "context_text": ctx_text
        }
    except Exception as e:
        _LOG.warning("retrieve_multimodal_context failed: %s", e)
        return {"results": [], "context": [], "context_text": ""}

