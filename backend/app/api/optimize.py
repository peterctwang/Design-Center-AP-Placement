"""GA optimization endpoint + WebSocket progress stream."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, SessionLocal
from ..models import Project, AccessPoint, OptimizationRun
from ..schemas import OptimizeRequest, TaskStarted
from ..task_hub import hub
from ..services.ga_service import run_ga_async

router = APIRouter(prefix="/api/projects/{project_id}", tags=["optimize"])


def _effective_bounds(project: Project) -> tuple[float, float, float, float]:
    """Use detected-wall bounding box (inset 0.5m), fall back to image extent."""
    if project.walls:
        xs = [p for w in project.walls for p in (w.p1_x, w.p2_x)]
        ys = [p for w in project.walls for p in (w.p1_y, w.p2_y)]
        return (min(xs) + 0.5, min(ys) + 0.5,
                max(xs) - 0.5, max(ys) - 0.5)
    if project.building_w_m and project.building_h_m:
        return (0.0, 0.0, project.building_w_m, project.building_h_m)
    raise HTTPException(400, "No walls and no building extent — upload first")


@router.post("/optimize", response_model=TaskStarted, status_code=202)
async def start_optimize(project_id: str, payload: OptimizeRequest,
                         db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")

    bounds = _effective_bounds(p)
    walls_for_ga = [
        {"p1": (w.p1_x, w.p1_y), "p2": (w.p2_x, w.p2_y),
         "material": w.material}
        for w in p.walls
    ]

    # Create a Run row to track status
    run = OptimizationRun(
        project_id=project_id,
        algorithm=payload.algorithm,
        target_coverage=payload.target_coverage,
        parameters=payload.model_dump(),
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    task_id = hub.new_task_id()

    def on_complete(result: dict):
        """Persist GA result. Runs in worker thread → use new DB session."""
        sess = SessionLocal()
        try:
            # Clear old APs
            sess.query(AccessPoint).filter(
                AccessPoint.project_id == project_id
            ).delete()
            for ap in result["aps"]:
                sess.add(AccessPoint(
                    project_id=project_id,
                    name=ap["name"], x=ap["x"], y=ap["y"], z=ap["z"],
                ))
            # Update run
            r = sess.get(OptimizationRun, run.id)
            if r:
                r.num_aps = result["num_aps"]
                r.final_coverage = result["coverage"]
                r.duration_sec = result["duration_sec"]
                r.status = "done"
            sess.commit()
        finally:
            sess.close()

    run_ga_async(
        task_id=task_id,
        bounds=bounds,
        walls=walls_for_ga,
        target_coverage=payload.target_coverage,
        num_aps=payload.num_aps,
        sqm_per_ap=payload.sqm_per_ap,
        on_complete=on_complete,
    )
    return TaskStarted(task_id=task_id, ws_url=f"/ws/tasks/{task_id}")


# ---------- List APs ----------

@router.get("/aps")
def list_aps(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    return [
        {"id": ap.id, "name": ap.name, "x": ap.x, "y": ap.y, "z": ap.z}
        for ap in p.aps
    ]
