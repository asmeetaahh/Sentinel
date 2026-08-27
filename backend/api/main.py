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

from backend.api.routers import ai, health, incidents, interventions, merchants, risk, simulator
from backend.api.state import load_state

DEV_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Vite falls through to the next free port (5174, 5175, ...) whenever the
# default is already taken by another local process — observed directly
# while integrating apps/dashboard, where 5173/5174 were occupied by
# unrelated processes on the dev machine. A fixed origin list is too
# brittle for local development, so any localhost/127.0.0.1 port is also
# allowed via regex; this only matters for a local, read-only,
# synthetic-benchmark API with no auth/session data, not a production
# CORS policy.
DEV_CORS_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1):\d+"


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
    allow_origin_regex=DEV_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    # POST added for the simulator endpoint (backend/api/routers/simulator.py)
    # — the only mutating-looking route in the API; it still never writes
    # anything to disk, it just runs the already-loaded model on a modified,
    # in-memory feature row.
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(merchants.router)
app.include_router(risk.router)
app.include_router(simulator.router)
app.include_router(incidents.router)
app.include_router(ai.router)
app.include_router(interventions.router)
