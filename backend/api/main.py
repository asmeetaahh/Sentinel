"""
Sentinel backend — FastAPI application.

Architecture (see docs/architecture/backend.md):
    data/artifacts (generator -> features -> model -> SHAP)
        -> backend/services, backend/risk  (thin, typed access layer)
        -> backend/api (FastAPI routes, request/response validation)
        -> future dashboard

This process loads the benchmark tables, the model artifact, and the SHAP
explainer exactly once at startup (backend/api/state.py) and serves every
request from that shared, read-only state — it never retrains, never
re-derives features, and never touches the synthetic generator.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import health, merchants, risk
from backend.api.state import load_state

DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_state()  # fail fast at startup if artifacts/data are missing, not on first request
    yield


app = FastAPI(
    title="Sentinel API",
    description=(
        "Synthetic-benchmark chargeback-risk research prototype, exposed through a backend API. "
        "Not production-ready. Not validated on real-world data. No access to real Razorpay systems or data."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEV_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(merchants.router)
app.include_router(risk.router)
