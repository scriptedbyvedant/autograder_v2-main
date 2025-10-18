from typing import List, Dict, Any, Optional
from collections import defaultdict

# Minimal in-memory RAG so you can run locally with no services.
# Swap with FAISS/Chroma + real embeddings in production.

class SimpleVectorStore:
    def __init__(self):
        self.items: List[Dict[str, Any]] = []
        self.by_q: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def add(self, doc_id: str, text: str, meta: Dict[str, Any]):
        self.items.append({"id": doc_id, "text": text, "meta": meta})
        if "q_id" in meta:
            self.by_q[meta["q_id"]].append({"id": doc_id, "text": text, "meta": meta})

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        qset = set((query or "").lower().split())
        scored = []
        for it in self.items:
            tset = set(it["text"].lower().split())
            score = len(qset & tset)
            scored.append((score, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:k]]

    def search_by_q(self, q_id: str, k: int = 3) -> List[Dict[str, Any]]:
        return self.by_q.get(q_id, [])[:k]


VS = SimpleVectorStore()


def retrieve_context(q_id: str, question: str, k: int = 3) -> Dict[str, Any]:
    """
    Pull rubric/ideal/exemplars for this question.
    """
    hits = VS.search_by_q(q_id, k=k) or VS.search(question, k=k)
    # Separate buckets
    rubric = next((h for h in hits if h["meta"].get("type") == "rubric"), None)
    ideal  = next((h for h in hits if h["meta"].get("type") == "ideal"), None)
    exemplars = [h for h in hits if h["meta"].get("type") == "exemplar"]
    return {
        "rubric": rubric["text"] if rubric else None,
        "ideal":  ideal["text"]  if ideal  else None,
        "exemplars": [{"text": e["text"], "meta": e["meta"]} for e in exemplars]
    }
