import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.middleware import ObservabilityAndSecurityMiddleware
from app.api.routes import router as api_router
from app.pipeline.embeddings import model_registry
from app.pipeline.retrieval import retrieval_pipe

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("DocMind")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management for graceful startup and shutdown."""
    logger.info(f"Starting {settings.PROJECT_NAME} (env: {settings.ENVIRONMENT})...")
    logger.info(f"Loaded Configuration: {settings.get_sanitized_dict()}")
    # Verify model loading
    _ = model_registry.dimension
    yield
    logger.info("Shutting down DocMind... Releasing resources.")
    retrieval_pipe.clear()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multimodal Intelligent Knowledge Copilot with Grounded Citations, Hybrid Retrieval & Evaluation Suite",
    lifespan=lifespan
)

# Custom Security & Tracing Middleware
app.add_middleware(ObservabilityAndSecurityMiddleware)

# Strict CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Global Sanitized Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Unhandled error for req_id={req_id}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please contact support with the request ID.",
            "request_id": req_id
        }
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health/live", tags=["Health"])
def liveness_check():
    """Kubernetes / Docker liveness probe."""
    return {"status": "alive", "service": settings.PROJECT_NAME}

@app.get("/health/ready", tags=["Health"])
def readiness_check():
    """Readiness probe checking model availability."""
    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "embedding_dimension": model_registry.dimension
    }

@app.get("/health", tags=["Health"])
def legacy_health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
