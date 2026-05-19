"""
Auto-detect walls (and infer material) from a floor plan image.

Uses OpenCV for line detection and color sampling. Works well on clean
schematic floor plans (like sample_floorplan.png). For photographs or
hand-drawn plans, swap this for Segment Anything later.

Pipeline:
  1. Load image, convert to multiple color masks (one per material color).
  2. For each mask, run morphology + HoughLinesP → line segments.
  3. Merge near-duplicate segments.
  4. Convert pixel coords to world meters using scale (px/m).

Returns:
  list of dicts: {'p1': (x_m, y_m), 'p2': (x_m, y_m), 'material': str}
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple

# Color signatures (BGR space, OpenCV native)
# Generous ranges to tolerate JPEG artifacts.
MATERIAL_HSV_RANGES = {
    # name : (lower_hsv, upper_hsv)
    'concrete': (np.array([0, 0, 0]), np.array([180, 60, 60])),       # near-black
    'brick':    (np.array([5, 80, 40]), np.array([25, 255, 220])),    # brown/orange
    'glass':    (np.array([80, 80, 80]), np.array([100, 255, 255])),  # cyan
    'metal':    (np.array([0, 0, 60]), np.array([180, 30, 130])),     # mid-gray
    'wood':     (np.array([10, 60, 100]), np.array([22, 200, 200])),  # tan
    'door':     (np.array([35, 60, 60]), np.array([80, 255, 240])),   # green (wider)
}

# Lines shorter than this (pixels) are noise
MIN_LINE_PX = 18

# When merging duplicate parallel lines, distance threshold (px)
MERGE_DIST = 8


def _detect_lines_for_mask(mask: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Extract line segments from a binary mask using HoughLinesP.

    Thick walls (3-5 px) are first SKELETONIZED to a 1-px centreline so we
    only get ONE line per wall (instead of one for each edge).
    """
    # Clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Skeletonize — collapses thick walls to their 1-pixel centreline
    try:
        from skimage.morphology import skeletonize
        skel = skeletonize(mask > 0).astype(np.uint8) * 255
    except Exception:
        skel = mask  # fallback if scikit-image missing

    lines = cv2.HoughLinesP(
        skel,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=MIN_LINE_PX,
        maxLineGap=15,
    )
    if lines is None:
        return []
    return [tuple(map(int, line[0])) for line in lines]


def _merge_lines(lines: List[Tuple[int, int, int, int]],
                 angle_tol_deg: float = 8.0,
                 offset_tol_px: float = 12.0,
                 gap_tol_px: float = 80.0) -> List[Tuple[int, int, int, int]]:
    """Merge COLLINEAR segments into long single lines.

    Two segments are merged if:
      - their angles match within `angle_tol_deg`
      - their perpendicular offset from origin matches within `offset_tol_px`
      - their projections on the shared line overlap or are within
        `gap_tol_px` of each other.
    The result is a single segment spanning from the minimum to maximum
    projection of all merged inputs.
    """
    if not lines:
        return []

    def angle(l):
        return np.arctan2(l[3] - l[1], l[2] - l[0])

    def normalize_angle(a):
        # map to [0, pi) — direction-agnostic
        a = a % np.pi
        return a

    # Compute line-equation params (theta, rho) for each segment
    segs = []
    for l in lines:
        x1, y1, x2, y2 = l
        theta = normalize_angle(angle(l))
        # Perpendicular distance from origin: rho = x*cos(theta+pi/2)+y*sin
        # Using line normal direction (perpendicular to segment)
        nx, ny = -np.sin(theta), np.cos(theta)
        rho = nx * x1 + ny * y1
        # Tangent direction along the line
        tx, ty = np.cos(theta), np.sin(theta)
        # Parametric coordinates along the line for both endpoints
        t1 = tx * x1 + ty * y1
        t2 = tx * x2 + ty * y2
        if t2 < t1:
            t1, t2 = t2, t1
        segs.append({
            'theta': theta, 'rho': rho, 'nx': nx, 'ny': ny,
            'tx': tx, 'ty': ty, 't_min': t1, 't_max': t2,
        })

    # Build groups: BFS over compatible segments
    used = [False] * len(segs)
    merged_out: list[tuple[int, int, int, int]] = []
    angle_tol = np.radians(angle_tol_deg)

    for i in range(len(segs)):
        if used[i]:
            continue
        group = [i]
        used[i] = True
        # find all collinear segments
        for j in range(len(segs)):
            if used[j]:
                continue
            si, sj = segs[i], segs[j]
            d_theta = abs(si['theta'] - sj['theta'])
            d_theta = min(d_theta, np.pi - d_theta)
            if d_theta > angle_tol:
                continue
            if abs(si['rho'] - sj['rho']) > offset_tol_px:
                continue
            # along-line projection overlap or gap
            overlap = not (sj['t_max'] < si['t_min'] - gap_tol_px or
                           sj['t_min'] > si['t_max'] + gap_tol_px)
            if not overlap:
                # also check vs the growing group's extent
                gt_min = min(segs[k]['t_min'] for k in group)
                gt_max = max(segs[k]['t_max'] for k in group)
                if (sj['t_max'] < gt_min - gap_tol_px or
                        sj['t_min'] > gt_max + gap_tol_px):
                    continue
            used[j] = True
            group.append(j)

        # Combine group: weighted average of theta/rho, span min..max
        ts = [segs[k]['theta'] for k in group]
        rs = [segs[k]['rho']   for k in group]
        # use median (robust)
        theta = float(np.median(ts))
        rho = float(np.median(rs))
        nx, ny = -np.sin(theta), np.cos(theta)
        tx, ty = np.cos(theta), np.sin(theta)
        t_min = min(segs[k]['t_min'] for k in group)
        t_max = max(segs[k]['t_max'] for k in group)
        # Reconstruct endpoints from line params: point = rho*n + t*tangent
        x1 = rho * nx + t_min * tx
        y1 = rho * ny + t_min * ty
        x2 = rho * nx + t_max * tx
        y2 = rho * ny + t_max * ty
        merged_out.append((int(x1), int(y1), int(x2), int(y2)))

    return merged_out


def _find_outer_wall_bbox(img_bgr) -> Tuple[int, int, int, int]:
    """Find bounding box of the outermost concrete wall.

    Robust method:
      1. Threshold for VERY DARK pixels only (concrete outer wall).
      2. For every row, find the leftmost & rightmost dark pixel.
      3. The MEDIAN of these gives the building's left/right edges
         (titles/scale bars affect only a few rows, so they're outliers).
      4. Same for top/bottom via columns.

    Falls back to all-material union if the dark-only method fails.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

    # For each ROW, where do dark pixels exist?
    lefts: list[int] = []
    rights: list[int] = []
    for y in range(h):
        cols = np.where(mask[y, :] > 0)[0]
        if cols.size > 3:                  # skip empty/noise-only rows
            lefts.append(int(cols.min()))
            rights.append(int(cols.max()))

    # For each COLUMN, where do dark pixels exist?
    tops: list[int] = []
    bottoms: list[int] = []
    for x in range(w):
        rows = np.where(mask[:, x] > 0)[0]
        if rows.size > 3:
            tops.append(int(rows.min()))
            bottoms.append(int(rows.max()))

    if not (lefts and rights and tops and bottoms):
        return _find_content_bbox_fallback(img_bgr)

    # === Get WALL CENTRE positions, not outer edges ===
    # For each row that contains the LEFT outer wall, find the centre of the
    # contiguous run of dark pixels starting from the leftmost dark pixel.
    # Same idea for right/top/bottom. This makes bbox edges land on the wall
    # CENTRELINES, so after cropping the wall centres are at cropped image
    # coordinates 0 (or W-1, H-1). Skeleton-based detection will produce
    # lines at exactly those same positions → pixel-perfect overlay.
    def _run_length_from(arr, start_idx, direction=1):
        n = len(arr); i = start_idx; run = 0
        while 0 <= i < n and arr[i] > 0:
            run += 1; i += direction
        return run

    left_centres, right_centres = [], []
    for y in range(h):
        row = mask[y]
        idx = np.where(row > 0)[0]
        if idx.size < 3:
            continue
        # Left wall: run starting at idx[0]
        run = _run_length_from(row, idx[0], 1)
        left_centres.append(idx[0] + run // 2)
        # Right wall: run starting at idx[-1] going leftwards
        run = _run_length_from(row, idx[-1], -1)
        right_centres.append(idx[-1] - run // 2)

    top_centres, bot_centres = [], []
    for x in range(w):
        col = mask[:, x]
        idx = np.where(col > 0)[0]
        if idx.size < 3:
            continue
        run = _run_length_from(col, idx[0], 1)
        top_centres.append(idx[0] + run // 2)
        run = _run_length_from(col, idx[-1], -1)
        bot_centres.append(idx[-1] - run // 2)

    if not (left_centres and right_centres and top_centres and bot_centres):
        return _find_content_bbox_fallback(img_bgr)

    x0 = int(np.median(left_centres))
    x1 = int(np.median(right_centres))
    y0 = int(np.median(top_centres))
    y1 = int(np.median(bot_centres))

    if (x1 - x0) < 0.3 * w or (y1 - y0) < 0.3 * h:
        return _find_content_bbox_fallback(img_bgr)
    return x0, y0, x1, y1


def _find_content_bbox_fallback(img_bgr, white_thresh: int = 240
                                 ) -> Tuple[int, int, int, int]:
    """Fallback: bbox of all non-white pixels."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    mask = (gray < white_thresh).astype(np.uint8) * 255
    coords = cv2.findNonZero(mask)
    if coords is None:
        h, w = img_bgr.shape[:2]
        return 0, 0, w, h
    x, y, w, h = cv2.boundingRect(coords)
    return x, y, x + w, y + h


def detect_walls_from_image(
    image_path: str,
    px_per_meter: float,
    origin_px: Tuple[int, int] = (0, 0),
    flip_y: bool = False,
    auto_crop: bool = True,
    building_width_m: float = None,
) -> Tuple[List[Dict], Dict]:
    """
    Detect walls per material and return them in world (meter) coords.

    Args:
        image_path: path to floor plan image
        px_per_meter: from caller (whole-image basis). Will be REPLACED with a
                      tighter content-area-based scale when `auto_crop=True`
                      and `building_width_m` is given.
        origin_px: pixel coordinate that maps to (0, 0) in world coords. When
                   auto_crop is enabled this is recomputed to the bbox's TL corner.
        flip_y:    set True if your world Y axis points up.
        auto_crop: if True, strip white margin and recompute scale + origin
                   so detected walls align with the visible floor plan.
        building_width_m: real-world width (m). Used only when auto_crop=True
                          to derive the corrected px_per_meter from the bbox.

    Returns:
        (walls, debug_info)
        walls: list of {p1, p2, material} in METERS
        debug_info: dict with counts per material + total + bbox info
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    info: Dict = {'image_shape': img.shape[:2]}

    if auto_crop:
        # Use the OUTER WALL contour as the building bbox — pixel-perfect.
        x0, y0, x1, y1 = _find_outer_wall_bbox(img)
        bbox_w_px = x1 - x0
        info['bbox'] = [int(x0), int(y0), int(x1), int(y1)]
        if building_width_m is not None and bbox_w_px > 0:
            px_per_meter = bbox_w_px / building_width_m
        origin_px = (x0, y0)
        info['px_per_meter'] = float(px_per_meter)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    all_walls: list[dict] = []

    ox, oy = origin_px
    for material, (lo, hi) in MATERIAL_HSV_RANGES.items():
        mask = cv2.inRange(hsv, lo, hi)
        lines_px = _detect_lines_for_mask(mask)
        lines_px = _merge_lines(lines_px)
        info[material] = len(lines_px)
        for x1p, y1p, x2p, y2p in lines_px:
            wx1 = (x1p - ox) / px_per_meter
            wy1 = (y1p - oy) / px_per_meter
            wx2 = (x2p - ox) / px_per_meter
            wy2 = (y2p - oy) / px_per_meter
            if flip_y:
                wy1 = -wy1; wy2 = -wy2
            all_walls.append({
                'p1': (wx1, wy1),
                'p2': (wx2, wy2),
                'material': material,
            })

    info['total_walls'] = len(all_walls)
    return all_walls, info


def walls_to_canvas_elements(walls: List[Dict]):
    """Convert detector output to GUI FloorPlanElement-compatible dicts."""
    from wifi_gui_app import MATERIAL_COLORS
    elements = []
    for w in walls:
        elements.append({
            'type': 'wall',
            'points': [w['p1'], w['p2']],
            'material': w['material'],
            'height': 3.0,
            'color': MATERIAL_COLORS.get(w['material'], '#000000'),
        })
    return elements
