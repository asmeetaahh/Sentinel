#!/usr/bin/env python3
"""
Start the Sentinel backend API for local development.

Usage:
    python scripts/run_backend.py
    python scripts/run_backend.py --port 8001 --no-reload

Then visit http://127.0.0.1:8000/docs for interactive API docs, or
http://127.0.0.1:8000/health for a liveness check.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload (default: reload enabled for development).")
    args = parser.parse_args()

    uvicorn.run("backend.api.main:app", host=args.host, port=args.port, reload=not args.no_reload)


if __name__ == "__main__":
    main()
