"""Walls endpoints: list, replace, detect-from-image."""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, Wall
from ..schemas import WallOut, WallsBulkIn
from ..services.cv_service import detect_walls

router = APIRouter(prefix="/api/projects/{project_id}/walls", tags=["walls"])


@router.get("", response_model=list[WallOut])
def list_walls(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p.walls


@router.put("", response_model=list[WallOut])
def replace_walls(project_id: str, payload: WallsBulkIn,
                   db: Session = Depends(get_db)):
    """Replace ALL walls of a project with the supplied list."""
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    # Delete existing
    for w in list(p.walls):
        db.delete(w)
    for w in payload.walls:
        db.add(Wall(project_id=project_id, **w.model_dump()))
    db.commit()
    return db.query(Wall).filter(Wall.project_id == project_id).all()


@router.post("/detect", response_model=list[WallOut])
def detect(project_id: str, db: Session = Depends(get_db)):
    """Auto-detect walls from the uploaded floor plan image."""
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if not p.image_path or not p.scale_px_per_m:
        raise HTTPException(400, "Upload a floor plan first")

    # Detector uses px_per_meter = image_w / building_w_m. This matches
    # the canvas coordinate system on the frontend, giving pixel-perfect
    # overlay between the image and the detected walls.
    img_path = Path(p.image_path)
    walls, info = detect_walls(
        img_path,
        px_per_meter=p.scale_px_per_m or 1.0,
        building_width_m=p.building_w_m,
    )

    # Replace walls
    for w in list(p.walls):
        db.delete(w)
    for w in walls:
        db.add(Wall(
            project_id=project_id,
            p1_x=w["p1"][0], p1_y=w["p1"][1],
            p2_x=w["p2"][0], p2_y=w["p2"][1],
            material=w["material"],
        ))
    db.commit()
    return db.query(Wall).filter(Wall.project_id == project_id).all()
