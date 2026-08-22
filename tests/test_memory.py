"""Memory: persistence, scoped retrieval, and similarity ranking."""
from memory.embeddings import cosine, embed
from shared.contracts import MemoryScope


def test_embedding_is_deterministic_and_normalised():
    a = embed("deploy failed on the staging environment")
    b = embed("deploy failed on the staging environment")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_similar_text_scores_higher_than_unrelated():
    q = embed("authentication token expired error")
    close = embed("the authentication token has expired")
    far = embed("kubernetes ingress load balancer routing")
    assert cosine(q, close) > cosine(q, far)


def test_experience_retrieval_influences_recall(memory):
    memory.record_experience("Fixed a null pointer in the payment gateway retry loop.",
                             tags=["payment"])
    memory.record_experience(
        "Rotated the expired JWT signing key to fix authentication failures.",
        tags=["auth"])
    # query shares vocabulary with the auth lesson (as real objectives do)
    results = memory.recall_experience("authentication failing after the token expired")
    assert results
    assert "jwt" in results[0].record.content.lower()


def test_scopes_are_isolated(memory):
    memory.record_session("run-1", "session-only note")
    memory.record_experience("long term lesson")
    long_term = memory.recall_experience("lesson")
    assert all(r.record.scope == MemoryScope.LONG_TERM for r in long_term)
    trace = memory.session_trace("run-1")
    assert any("session-only" in r.content for r in trace)
