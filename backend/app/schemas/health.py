from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    api: Literal["ok"]
    demo_mode: bool


class HealthResponse(LivenessResponse):
    database: Literal["ok", "error"]
    redis: Literal["ok", "error"]
