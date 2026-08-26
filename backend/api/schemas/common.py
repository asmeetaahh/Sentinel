from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Provenance = Literal["observed", "modeled", "derived"]


class ErrorResponse(BaseModel):
    detail: str
