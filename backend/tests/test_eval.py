import pytest
from app.eval.benchmark import RAGEvaluationHarness

def test_hit_rate_calculation():
    harness = RAGEvaluationHarness()
    retrieved = [
        ["doc_a", "doc_b", "doc_c"],
        ["doc_x", "doc_y", "doc_z"],
        ["doc_1", "doc_2", "doc_3"]
    ]
    expected = ["doc_b", "doc_w", "doc_1"]

    # 2 hits out of 3 queries -> 0.6667
    hit_rate = harness.calculate_hit_rate_at_k(retrieved, expected, k=3)
    assert hit_rate == 0.6667

def test_mrr_calculation():
    harness = RAGEvaluationHarness()
    retrieved = [
        ["doc_a", "doc_b"], # expected is doc_a -> rank 1 (1.0)
        ["doc_x", "doc_y"], # expected is doc_y -> rank 2 (0.5)
        ["doc_1", "doc_2"]  # expected is doc_9 -> rank inf (0.0)
    ]
    expected = ["doc_a", "doc_y", "doc_9"]
    # (1.0 + 0.5 + 0.0) / 3 = 0.5000
    mrr = harness.calculate_mrr(retrieved, expected)
    assert mrr == 0.5000

def test_faithfulness_calculation():
    harness = RAGEvaluationHarness()
    ctx = "The operating revenue grew by 18 percent in the third quarter."
    ans = "Operating revenue grew by 18 percent."
    score = harness.calculate_faithfulness(ctx, ans)
    assert score > 0.80

    # Completely ungrounded
    hallucinated = "Quantum teleportation was discovered on Mars."
    low_score = harness.calculate_faithfulness(ctx, hallucinated)
    assert low_score < 0.20
