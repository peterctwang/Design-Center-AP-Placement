"""GA runner — uses BackgroundTasks + thread + task_hub for progress."""
import asyncio
import threading
import time
from typing import Callable
from loguru import logger

from algorithms.genetic_optimizer import (
    optimize_ap_placement,
    optimize_ap_placement_auto,
    elements_to_walls,
)
from ..task_hub import hub


def _wall_models_to_optimizer_format(walls_db) -> list[dict]:
    """Convert SQLAlchemy Wall rows -> list of dicts the optimizer expects."""
    return [
        {
            "p1": (w.p1_x, w.p1_y),
            "p2": (w.p2_x, w.p2_y),
            "material": w.material,
        }
        for w in walls_db
    ]


def run_ga_async(
    task_id: str,
    bounds: tuple[float, float, float, float],
    walls: list[dict],
    target_coverage: float,
    num_aps: int,
    sqm_per_ap: float,
    on_complete: Callable[[dict], None],
) -> None:
    """Schedule GA in a worker thread; publish progress via task_hub.

    `on_complete(result_dict)` runs in worker thread after GA finishes.
    """
    # Must be called from an async context (FastAPI async handler)
    loop = asyncio.get_running_loop()
    hub.register_loop(task_id, loop)

    def worker():
        try:
            start = time.time()
            hub.publish(task_id, {"stage": "starting", "progress": 0})

            auto_mode = num_aps == 0
            if auto_mode:
                def progress_cb(stage=None, n=None):
                    hub.publish(task_id, {
                        "stage": stage or f"N={n}",
                        "progress": 50,
                    })
                result, n, cov = optimize_ap_placement_auto(
                    bounds=bounds,
                    walls=walls,
                    target_coverage=target_coverage,
                    min_n=2, max_n=16,
                    sqm_per_ap=sqm_per_ap,
                    progress_cb=progress_cb,
                    population_size=50,
                    n_generations=40,
                    sample_resolution=20,
                )
            else:
                def progress_cb_fixed(gen, cov):
                    hub.publish(task_id, {
                        "stage": f"gen {gen}",
                        "progress": (gen + 1) / 40 * 100,
                        "coverage": cov,
                    })
                result = optimize_ap_placement(
                    bounds=bounds, walls=walls, num_aps=num_aps,
                    population_size=50, n_generations=40,
                    sample_resolution=20, progress_cb=progress_cb_fixed,
                )
                # Measure coverage afterwards
                from algorithms.genetic_optimizer import _measure_coverage
                cov = _measure_coverage(result, walls, bounds, resolution=20)
                n = num_aps

            duration = time.time() - start
            payload = {
                "num_aps": n,
                "coverage": float(cov),
                "duration_sec": duration,
                "aps": [
                    {"name": name, "x": float(x), "y": float(y), "z": float(z)}
                    for name, (x, y, z) in result.items()
                ],
            }
            hub.set_result(task_id, payload)
            on_complete(payload)
            hub.publish(task_id, {"done": True, "result": payload})
        except Exception as e:
            logger.exception("GA failed")
            hub.publish(task_id, {"error": str(e)})

    threading.Thread(target=worker, daemon=True).start()
