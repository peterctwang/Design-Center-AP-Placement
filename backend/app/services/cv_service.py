"""Wraps algorithms/wall_detector.py for the web API."""
from pathlib import Path
from loguru import logger

from algorithms.wall_detector import detect_walls_from_image


def detect_walls(
    image_path: Path,
    px_per_meter: float,
    building_width_m: float | None = None,
) -> tuple[list[dict], dict]:
    """Run OpenCV wall detection on a floor plan image.

    IMPORTANT: We use the FULL image width as the meter reference
    (px_per_meter = image_w / building_width_m), matching the Desktop
    GUI's behaviour. Walls land in the same coordinate space as the
    image rendered in the React canvas, so they overlay PIXEL-PERFECT.

    Returns:
        walls: list of {p1, p2, material} in METERS (origin = image top-left)
        info:  detector stats
    """
    logger.info(
        f"CV detect walls: {image_path}, px/m={px_per_meter}, "
        f"building_w={building_width_m}"
    )
    walls, info = detect_walls_from_image(
        image_path=str(image_path),
        px_per_meter=px_per_meter,
        auto_crop=False,                  # ← Desktop behaviour
        building_width_m=building_width_m,
    )
    logger.info(f"CV result: {info}")
    return walls, info
