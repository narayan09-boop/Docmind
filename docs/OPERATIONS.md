# DocMind Operations & Site Reliability Runbook

## 1. Service Level Objectives (SLOs)

| Metric | Target | Measurement Method | Alert Threshold |
| :--- | :--- | :--- | :--- |
| **Availability** | 99.9% uptime | `GET /health/live` probe success rate over 30d window | Uptime < 99.5% over 15m |
| **Inference Latency** | p95 < 200ms (Cache hit), p95 < 1200ms (Cold query) | Middleware `duration_ms` metric | p95 > 2500ms for 5m |
| **Retrieval Accuracy** | Hit Rate@3 $\ge$ 90% | Automated benchmark test run | Hit Rate@3 < 85% |
| **Error Rate** | < 0.5% 5xx errors | Access log HTTP 500 status counter | 5xx rate > 1.0% over 5m |

---

## 2. Structured Log Schema

All HTTP access events emit structured log lines:

```text
2026-10-21 21:30:15 [INFO] DocMind.Access - req_id=f47ac10b-58cc-4372-a567-0e02b2c3d479 method=POST path=/api/v1/query status=200 duration_ms=28.4
```

Fields:
- `timestamp`: UTC ISO-8601 timestamp.
- `req_id`: Correlation ID passed via `X-Request-ID` or generated per request.
- `method`: HTTP method (GET, POST, OPTIONS).
- `path`: Normalized route endpoint.
- `status`: HTTP response status code.
- `duration_ms`: End-to-end request latency in milliseconds.

---

## 3. Incident Response & Troubleshooting Runbook

### Scenario A: High Memory Usage / Container OOM Crashes
1. Inspect active chunk count: `GET /api/v1/stats`.
2. Check if an oversized document bypassed limits: search logs for `MAX_UPLOAD_SIZE_BYTES`.
3. Clear in-memory caches: trigger restart or invoke `retrieval_pipe.clear()`.

### Scenario B: Cross-Encoder Reranker Latency Spikes
1. Check CPU throttling: ensure Docker compose resource limit allows at least 2 CPU cores.
2. If running on low-resource VMs, set `ENABLE_RERANKER=false` in `.env` to fall back to pure RRF rank ordering.

### Scenario C: Rate Limit 429 False Positives
1. Check if client traffic originates from a corporate proxy or reverse proxy without `X-Forwarded-For`.
2. Increase `RATE_LIMIT_PER_MINUTE` in configuration.
