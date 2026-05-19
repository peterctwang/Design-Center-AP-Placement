"""Project CRUD endpoints (no auth required)."""
import re
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import aiofiles
from PIL import Image

# Make algorithms importable for upload-time auto-cropping
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ..db import get_db
from ..models import Project
from ..schemas import ProjectCreate, ProjectOut
from ..config import settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name, building_type=payload.building_type)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if p.image_path:
        try:
            Path(p.image_path).unlink(missing_ok=True)
        except Exception:
            pass
    db.delete(p)
    db.commit()


# ---------- Floor plan upload ----------

DIM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m", re.IGNORECASE)
SINGLE_DIM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*m", re.IGNORECASE)


@router.post("/{project_id}/upload", response_model=ProjectOut)
async def upload_floor_plan(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")

    # === Cleanup any old image / walls / APs (image dims may change!) ===
    if p.image_path:
        try:
            Path(p.image_path).unlink(missing_ok=True)
        except Exception:
            pass
    # Also delete any leftover files for this project with other extensions
    for ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        for tag in ("", "_raw"):
            f = settings.upload_dir / f"{project_id}{tag}{ext}"
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
    # Clear walls and APs (old coords no longer valid after image change)
    for w in list(p.walls):
        db.delete(w)
    for ap in list(p.aps):
        db.delete(ap)
    db.flush()

    # Save raw upload
    suffix = Path(file.filename or "image.png").suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
        raise HTTPException(400, f"Unsupported file type: {suffix}")
    raw_dest = settings.upload_dir / f"{project_id}_raw{suffix}"
    async with aiofiles.open(raw_dest, "wb") as fout:
        await fout.write(await file.read())

    # Parse intended building dimensions from filename
    name = file.filename or ""
    m = DIM_RE.search(name)
    h_m_hint: float | None = None
    if m:
        w_m_hint: float = float(m.group(1))
        h_m_hint = float(m.group(2))
    else:
        m2 = SINGLE_DIM_RE.search(name)
        w_m_hint = float(m2.group(1)) if m2 else 20.0

    # === AUTO-CROP to actual building extent ===
    # Detect the outer wall bbox so the saved image IS the building only.
    # This guarantees pixel-perfect overlay: image bounds == wall bounds.
    import cv2
    from algorithms.wall_detector import _find_outer_wall_bbox
    img_bgr = cv2.imread(str(raw_dest))
    if img_bgr is None:
        raise HTTPException(400, "Could not read uploaded image")
    x0, y0, x1, y1 = _find_outer_wall_bbox(img_bgr)
    bbox_w_px = x1 - x0
    bbox_h_px = y1 - y0
    cropped = img_bgr[y0:y1, x0:x1]
    final_dest = settings.upload_dir / f"{project_id}{suffix}"
    cv2.imwrite(str(final_dest), cropped)
    # Optional: drop the raw upload to keep things tidy
    try:
        raw_dest.unlink(missing_ok=True)
    except Exception:
        pass

    # Final image now represents the building exactly.
    # Always use the CROPPED IMAGE'S ASPECT RATIO so canvas rendering
    # is pixel-perfect — even if the filename's HxW hint doesn't match
    # the image's actual proportions (it usually has slight margin error).
    w_m = w_m_hint
    h_m = w_m * (bbox_h_px / bbox_w_px)
    scale = bbox_w_px / w_m   # px per meter (now exact)

    p.image_path = str(final_dest)
    p.scale_px_per_m = scale
    p.building_w_m = w_m
    p.building_h_m = h_m
    db.commit()
    db.refresh(p)
    return p
