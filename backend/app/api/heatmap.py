"""Compute heatmap on-demand using the GA-compatible signal model."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project
from ..services.heatmap_service import compute_heatmap
from .optimize import _effective_bounds

router = APIRouter(prefix="/api/projects/{project_id}", tags=["heatmap"])


@router.get("/heatmap")
def get_heatmap(
    project_id: str,
    mode: str = Query("signal_strength",
                      pattern="^(signal_strength|coverage|interference|sinr)$"),
    resolution: int = Query(80, ge=20, le=200),
    db: Session = Depends(get_db),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if not p.aps:
        raise HTTPException(400, "No APs yet — run /optimize first")

    bounds = _effective_bounds(p)
    walls = [
        {"p1": (w.p1_x, w.p1_y), "p2": (w.p2_x, w.p2_y),
         "material": w.material}
        for w in p.walls
    ]
    aps = [(ap.x, ap.y) for ap in p.aps]

    return compute_heatmap(bounds=bounds, walls=walls, aps=aps,
                           resolution=resolution, mode=mode)
