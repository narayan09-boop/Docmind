# DocMind Quantitative Evaluation Framework

## 1. Evaluation Methodology

DocMind includes an automated, dataset-driven evaluation framework independent of the real-time serving path. It assesses retrieval relevance, ranking accuracy, groundedness, and hallucination resistance against standardized test corpuses.

---

## 2. Mathematical Metric Definitions

### 1. Hit Rate@K
The percentage of queries where at least one ground-truth document excerpt appears in the top-$K$ retrieved results:
$$\text{Hit Rate}@K = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \mathbb{I}\left( \text{expected\_doc}_q \in \text{retrieved}_{1..K}(q) \right)$$

### 2. Mean Reciprocal Rank (MRR)
Measures the ranking position of the first relevant document:
$$\text{MRR} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\text{rank}_q}$$
Where $\text{rank}_q$ is the 1-based index of the first relevant item retrieved, or $0$ if not found.

### 3. Precision@K
Measures the proportion of retrieved chunks that contain expected factual evidence:
$$\text{Precision}@K = \frac{|\text{retrieved}_{1..K} \cap \text{expected\_evidence}|}{K}$$

### 4. Faithfulness (Groundedness Score)
Evaluates whether statements in the answer are strictly entailed by the retrieved document passages without hallucination:
$$\text{Faithfulness} = \frac{|\text{Tokens}_{\text{Answer}} \cap \text{Tokens}_{\text{Context}}|}{|\text{Tokens}_{\text{Answer}}|}$$

---

## 3. Benchmark Dataset Schema

Evaluation datasets are versioned JSON documents structured as follows:

```json
{
  "dataset_name": "DocMind Financial & Technical Benchmark",
  "version": "1.0.0",
  "examples": [
    {
      "id": "eval-001",
      "query": "What was the total operating revenue expansion for Q3?",
      "expected_doc": "Q3_Financial_Analysis_Report.pdf",
      "expected_keywords": ["18.4%", "$4.2B"],
      "reference_answer": "Total operating revenue expanded by 18.4% YoY to $4.2B.",
      "category": "financial_metric"
    }
  ]
}
```

---

## 4. Running Benchmarks

### Via CLI
```bash
cd backend
python -m app.eval.benchmark
```

### Via API Endpoint
```bash
curl -X GET http://localhost:8000/api/v1/eval/benchmark \
  -H "X-Tenant-ID: default"
```

Results are saved to `docs/eval_results.json`.
