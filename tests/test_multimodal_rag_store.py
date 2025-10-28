from grader_engine.multimodal_rag import MultimodalVectorStore


def test_vector_store_add_and_search():
    store = MultimodalVectorStore()
    store.add("q1-text", "Explain supervised learning techniques", "text", {"q_id": "Q1", "type": "question"})
    store.add("q1-ideal", "Models learn from labelled data to map inputs to outputs", "text", {"q_id": "Q1", "type": "ideal"})
    store.add("q2-text", "Describe gradient descent for neural networks", "text", {"q_id": "Q2", "type": "question"})

    results = store.search("labelled data learning", top_k=2)

    assert isinstance(results, list)
    if results:
        first = results[0]
        assert "text" in first
        assert "meta" in first
