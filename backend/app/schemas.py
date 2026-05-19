"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ---------- Project ----------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    building_type: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    building_type: str | None = None
    image_path: str | None = None
    scale_px_per_m: float | None = None
    building_w_m: float | None = None
    building_h_m: float | None = None
    ceiling_h_m: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Wall ----------

Material = Literal["concrete", "brick", "glass", "wood", "drywall", "metal", "door"]


class WallIn(BaseModel):
    p1_x: float
    p1_y: float
    p2_x: float
    p2_y: float
    material: Material = "concrete"
    height: float = 3.0


class WallOut(WallIn):
    id: str

    class Config:
        from_attributes = True


class WallsBulkIn(BaseModel):
    walls: list[WallIn]


# ---------- Access Point ----------

class APOut(BaseModel):
    id: str
    name: str
    x: float
    y: float
    z: float
    tx_power_dbm: float
    freq_ghz: float

    class Config:
        from_attributes = True


# ---------- Optimize ----------

class OptimizeRequest(BaseModel):
    algorithm: Literal["ga", "grid"] = "ga"
    target_coverage: float = Field(0.9, ge=0.5, le=1.0)
    num_aps: int = Field(0, ge=0, le=50)         # 0 = auto
    sqm_per_ap: float = Field(120.0, ge=30.0, le=500.0)


class TaskStarted(BaseModel):
    task_id: str
    ws_url: str


# ---------- Heatmap ----------

HeatmapMode = Literal["signal_strength", "coverage", "interference", "sinr"]


class HeatmapRequest(BaseModel):
    mode: HeatmapMode = "signal_strength"
    resolution: int = Field(80, ge=20, le=200)


# ---------- Detect Walls ----------

class DetectRequest(BaseModel):
    building_width_m: float = Field(ge=1.0, le=500.0)
