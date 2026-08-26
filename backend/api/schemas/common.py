from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Provenance = Literal["observed", "modeled", "derived", "synthetic_prototype"]
"""
observed             — read directly from generated benchmark data.
modeled              — output of the saved, validated ML artifact.
derived              — computed transparently from the above (not a model).
synthetic_prototype  — a Sentinel-prototype construct with no real-world
                        analog and no benchmark data proxy (e.g. the
                        incident layer's reason-code taxonomy, or an
                        evidence-availability rule with no observable
                        signal to derive from) — always explicitly labeled
                        as such, never presented as observed/modeled/derived.
"""


class ErrorResponse(BaseModel):
    detail: str
