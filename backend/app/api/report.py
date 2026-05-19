"""PDF report endpoint."""
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project
from ..config import settings
from ..services.heatmap_service import compute_heatmap
from ..services.pdf_service import generate_pdf
from .optimize import _effective_bounds

router = APIRouter(prefix="/api/projects/{project_id}", tags=["report"])


@router.get("/report.pdf")
def download_report(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if not p.aps:
        raise HTTPException(400, "No APs to report — run /optimize first")

    # Quick heatmap stats
    bounds = _effective_bounds(p)
    walls = [
        {"p1": (w.p1_x, w.p1_y), "p2": (w.p2_x, w.p2_y),
         "material": w.material} for w in p.walls
    ]
    aps_xy = [(ap.x, ap.y) for ap in p.aps]
    hm = compute_heatmap(bounds, walls, aps_xy, resolution=40,
                         mode="signal_strength")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = settings.report_dir / f"{project_id}_{ts}.pdf"

    generate_pdf(
        output_path=pdf_path,
        project_name=p.name,
        image_path=Path(p.image_path) if p.image_path else None,
        walls_count=len(p.walls),
        aps=[{"name": ap.name, "x": ap.x, "y": ap.y, "z": ap.z} for ap in p.aps],
        coverage_pct=hm["covered_pct"],
        avg_rssi=hm["avg_rssi"],
    )
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"{p.name}_report.pdf")
