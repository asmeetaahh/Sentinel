from __future__ import annotations

from backend.api.state import AppState, load_state


def get_state() -> AppState:
    return load_state()
