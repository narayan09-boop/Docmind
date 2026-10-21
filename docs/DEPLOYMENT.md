# DocMind Production Deployment Guide

## 1. Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- Python 3.10+ (if deploying directly to bare metal / VM)
- Node.js 18+ (for frontend)
- Minimum System Resources: 2 CPU Cores, 4GB RAM (8GB recommended if hosting local models)

---

## 2. Docker Compose Deployment (Recommended)

1. **Clone repository & prepare environment**:
   ```bash
   git clone https://github.com/narayan09-boop/Docmind.git
   cd Docmind
   cp .env.example .env
   # Edit .env with production parameters
   ```

2. **Launch all services**:
   ```bash
   docker-compose up --build -d
   ```

3. **Verify running containers & health status**:
   ```bash
   docker-compose ps
   ```

---

## 3. Production Environment Variables Reference

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Yes | `production` | Set to `production` to activate strict security checks. |
| `ALLOWED_ORIGINS` | Yes | `["https://yourdomain.com"]` | JSON array of trusted frontend domains (no wildcards allowed in production). |
| `API_KEY` | Optional | `None` | Master token for authenticating API requests. |
| `LLM_PROVIDER` | Yes | `local` | `openai`, `ollama`, or `local`. |
| `OPENAI_API_KEY` | If provider=openai | `None` | Production OpenAI API token. |
| `REDIS_URL` | Optional | `None` | Redis connection URL for distributed semantic cache. |
| `RATE_LIMIT_PER_MINUTE`| Optional | `60` | Client request throttling ceiling. |

---

## 4. Container Health & Readiness Probes

- **Liveness Probe**: `GET /health/live` (Returns HTTP 200 `{"status": "alive"}`)
- **Readiness Probe**: `GET /health/ready` (Returns HTTP 200 when models and dependencies are initialized)
