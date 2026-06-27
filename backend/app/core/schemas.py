from typing import Literal

from pydantic import BaseModel, Field


class VisionTouchConfigUpdate(BaseModel):
    enabled: bool | None = None
    tracking_mode: Literal["hand", "color_marker"] | None = None
    smoothing_alpha: float | None = Field(default=None, ge=0.05, le=0.95)
    click_cooldown_ms: int | None = Field(default=None, ge=100, le=3000)
    active_area_min: int | None = Field(default=None, ge=100)
    active_area_max: int | None = Field(default=None, ge=1000)
    press_hold_ms: int | None = Field(default=None, ge=100, le=2000)
