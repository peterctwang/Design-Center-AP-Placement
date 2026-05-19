"""
Real Multi-Objective Genetic Algorithm for AP Placement using DEAP.

Replaces the grid-only "intelligent placement" with NSGA-II optimization.
Objectives:
  1. Maximize coverage (% of grid points with RSSI >= threshold)
  2. Minimize average signal weakness (lower is better)
  3. Minimize AP count (handled via fixed-size individual; tuned by caller)

Author: Custom implementation for AI Wall Design System
"""

import random
import logging
import math
from typing import List, Tuple, Dict, Optional, Any

import numpy as np
from deap import base, creator, tools, algorithms

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# Signal model — Multi-Wall (ITU-R P.1238 inspired)
# ----------------------------------------------------------------------------

DEFAULT_TX_POWER_DBM = 20.0       # AP transmit power
DEFAULT_FREQ_GHZ = 2.4
COVERAGE_THRESHOLD_DBM = -65.0    # "covered" if RSSI above this
NOISE_FLOOR_DBM = -95.0

# Indoor path-loss exponent — typical indoor office/residential value.
# n = 2.0 is FREE SPACE (unrealistic indoor)
# n = 3.0 is TYPICAL OFFICE with furniture/people
# n = 3.5 is DENSE COMMERCIAL (warehouse, server room)
PATH_LOSS_EXPONENT = 3.0
REFERENCE_DISTANCE_M = 1.0
REFERENCE_PATH_LOSS_DB = 40.0     # PL at 1m for 2.4 GHz (Friis @1m)

# Wall attenuation per material (2.4 GHz, dB per traversal)
WALL_ATTEN = {
    'concrete': 12.0,
    'brick': 6.0,
    'glass': 3.0,
    'wood': 4.0,
    'drywall': 3.0,
    'metal': 20.0,
    'door': 3.0,    # closed wood door — light loss
    'air': 0.0,
}


def free_space_path_loss(distance_m: float, freq_ghz: float = DEFAULT_FREQ_GHZ) -> float:
    """Pure FSPL (kept for reference)."""
    d = max(distance_m, 0.5)
    return 20 * math.log10(d) + 20 * math.log10(freq_ghz) + 32.44


def indoor_path_loss(distance_m: float, n: float = PATH_LOSS_EXPONENT) -> float:
    """Log-distance indoor model:
        PL(d) = PL(d0) + 10 * n * log10(d/d0)
    Use n=3.0 for typical office, 3.5 for dense / warehouse.
    """
    d = max(distance_m, REFERENCE_DISTANCE_M)
    return REFERENCE_PATH_LOSS_DB + 10.0 * n * math.log10(d / REFERENCE_DISTANCE_M)


def segment_intersects(p1, p2, w1, w2) -> bool:
    """Check whether segment p1-p2 intersects wall segment w1-w2 (2D)."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, w1, w2) != ccw(p2, w1, w2) and ccw(p1, p2, w1) != ccw(p1, p2, w2)


def rssi_at_point(ap_xy, point_xy, walls, tx_power=DEFAULT_TX_POWER_DBM,
                  freq_ghz=DEFAULT_FREQ_GHZ,
                  path_loss_n: float = PATH_LOSS_EXPONENT) -> float:
    """Compute RSSI at a point using INDOOR log-distance model + wall losses."""
    dx = ap_xy[0] - point_xy[0]
    dy = ap_xy[1] - point_xy[1]
    distance = math.sqrt(dx * dx + dy * dy)

    path_loss = indoor_path_loss(distance, n=path_loss_n)

    wall_loss = 0.0
    for wall in walls:
        if segment_intersects(ap_xy, point_xy, wall['p1'], wall['p2']):
            wall_loss += WALL_ATTEN.get(wall.get('material', 'concrete'),
                                        WALL_ATTEN['concrete'])

    return tx_power - path_loss - wall_loss


# ----------------------------------------------------------------------------
# Fitness evaluation
# ----------------------------------------------------------------------------

def _point_segment_distance(p, a, b):
    """Shortest distance from point p to segment a-b (all 2D)."""
    ax, ay = a; bx, by = b; px, py = p
    abx = bx - ax; aby = by - ay
    t = 0.0
    denom = abx * abx + aby * aby
    if denom > 1e-9:
        t = ((px - ax) * abx + (py - ay) * aby) / denom
        t = max(0.0, min(1.0, t))
    cx = ax + t * abx; cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def _walls_to_arrays(walls):
    """Pack walls into numpy arrays for vectorized intersection tests.

    Returns:
      W1, W2 : (M, 2) float arrays — endpoints of each wall
      LOSS   : (M,)   float array  — attenuation in dB per wall
    """
    if not walls:
        return (np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0,)))
    W1 = np.array([w['p1'] for w in walls], dtype=float)
    W2 = np.array([w['p2'] for w in walls], dtype=float)
    LOSS = np.array(
        [WALL_ATTEN.get(w.get('material', 'concrete'), WALL_ATTEN['concrete'])
         for w in walls], dtype=float,
    )
    return W1, W2, LOSS


def _rssi_vectorized(ap_xy, sample_points, W1, W2, LOSS,
                     tx_power=DEFAULT_TX_POWER_DBM, n=PATH_LOSS_EXPONENT):
    """Compute RSSI from a single AP to ALL sample points at once.

    All array ops in NumPy → ~30-50x faster than Python loop on dense walls.

    Args:
        ap_xy: (2,) tuple/array
        sample_points: (N, 2) array
        W1, W2: (M, 2) wall endpoint arrays
        LOSS:   (M,)   wall attenuation
    Returns:
        rssi: (N,) array of RSSI values
    """
    ap = np.asarray(ap_xy, dtype=float)
    P = sample_points

    # Path loss
    d = np.maximum(np.linalg.norm(P - ap, axis=1), REFERENCE_DISTANCE_M)
    path_loss = REFERENCE_PATH_LOSS_DB + 10.0 * n * np.log10(d / REFERENCE_DISTANCE_M)

    # Wall losses: vectorized segment intersection of (ap -> P[i]) vs each wall
    if W1.shape[0] == 0:
        return tx_power - path_loss

    # CCW orientation predicate for many segments
    def _ccw(a, b, c):
        return (c[..., 1] - a[..., 1]) * (b[..., 0] - a[..., 0]) > \
               (b[..., 1] - a[..., 1]) * (c[..., 0] - a[..., 0])

    N = P.shape[0]; M = W1.shape[0]
    # Broadcast: A = ap (1,1,2), B = P (N,1,2), W1 (1,M,2), W2 (1,M,2)
    A = ap[None, None, :]
    B = P[:, None, :]
    W1b = W1[None, :, :]
    W2b = W2[None, :, :]

    cross1 = _ccw(A, W1b, W2b) != _ccw(B, W1b, W2b)   # (N, M)
    cross2 = _ccw(A, B, W1b) != _ccw(A, B, W2b)
    intersects = cross1 & cross2                       # (N, M) bool

    wall_loss = (intersects * LOSS[None, :]).sum(axis=1)
    return tx_power - path_loss - wall_loss


def evaluate_individual(individual: List[float],
                        sample_points: np.ndarray,
                        walls: List[Dict],
                        bounds: Tuple[float, float, float, float],
                        num_aps: int,
                        min_wall_dist: float = 0.5,
                        min_ap_sep: float = 3.0,
                        wall_arrays: Optional[Tuple] = None) -> Tuple[float, float]:
    """
    Fitness with multiple penalties so GA avoids doorways / wall-hugging /
    AP clustering.

    Returns (neg_coverage, avg_weakness_with_penalty) — both minimized.
    """
    aps = [(individual[i * 2], individual[i * 2 + 1]) for i in range(num_aps)]

    if wall_arrays is None:
        wall_arrays = _walls_to_arrays(walls)
    W1, W2, LOSS = wall_arrays

    best_rssi = np.full(len(sample_points), NOISE_FLOOR_DBM)
    for ap in aps:
        rssi = _rssi_vectorized(ap, sample_points, W1, W2, LOSS)
        best_rssi = np.maximum(best_rssi, rssi)

    covered = np.sum(best_rssi >= COVERAGE_THRESHOLD_DBM)
    coverage_pct = covered / len(sample_points)
    avg_weakness = -np.mean(best_rssi)

    min_x, min_y, max_x, max_y = bounds
    penalty = 0.0

    # 1) Out-of-bounds
    for x, y in aps:
        if not (min_x <= x <= max_x and min_y <= y <= max_y):
            penalty += 5.0

    # 2) Too close to a wall (within min_wall_dist meters)
    for x, y in aps:
        for w in walls:
            d = _point_segment_distance((x, y), w['p1'], w['p2'])
            if d < min_wall_dist:
                penalty += (min_wall_dist - d) * 2.0  # graded penalty
                break  # one penalty per AP

    # 3) Two APs too close together (clustering)
    for i in range(len(aps)):
        for j in range(i + 1, len(aps)):
            d = math.hypot(aps[i][0] - aps[j][0], aps[i][1] - aps[j][1])
            if d < min_ap_sep:
                penalty += (min_ap_sep - d) * 0.5

    return (-coverage_pct + penalty * 0.05,
            avg_weakness + penalty * 5.0)


# ----------------------------------------------------------------------------
# Main GA entry point
# ----------------------------------------------------------------------------

# Register types once (DEAP complains if redefined)
if not hasattr(creator, "FitnessMultiAP"):
    creator.create("FitnessMultiAP", base.Fitness, weights=(-1.0, -1.0))
if not hasattr(creator, "IndividualAP"):
    creator.create("IndividualAP", list, fitness=creator.FitnessMultiAP)


def optimize_ap_placement(bounds: Tuple[float, float, float, float],
                          walls: List[Dict],
                          num_aps: int = 4,
                          population_size: int = 50,
                          n_generations: int = 40,
                          sample_resolution: int = 25,
                          seed: Optional[int] = 42,
                          progress_cb=None) -> Dict[str, Tuple[float, float, float]]:
    """
    Run NSGA-II to find optimal AP placement.

    Args:
        bounds: (min_x, min_y, max_x, max_y) in meters
        walls: list of {'p1': (x,y), 'p2': (x,y), 'material': str}
        num_aps: fixed number of APs to place
        population_size: GA population
        n_generations: GA generations
        sample_resolution: grid resolution for fitness evaluation
        seed: RNG seed for reproducibility
        progress_cb: optional callable(generation, best_coverage) for UI updates

    Returns:
        dict {AP_name: (x, y, z)} of best solution.
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    min_x, min_y, max_x, max_y = bounds

    # Sample grid for fitness evaluation
    xs = np.linspace(min_x + 0.5, max_x - 0.5, sample_resolution)
    ys = np.linspace(min_y + 0.5, max_y - 0.5, sample_resolution)
    sample_points = np.array([(x, y) for x in xs for y in ys])

    toolbox = base.Toolbox()

    def make_gene_x():
        return random.uniform(min_x + 1.0, max_x - 1.0)

    def make_gene_y():
        return random.uniform(min_y + 1.0, max_y - 1.0)

    def init_individual():
        coords = []
        for _ in range(num_aps):
            coords.append(make_gene_x())
            coords.append(make_gene_y())
        return creator.IndividualAP(coords)

    # Pre-pack walls once for vectorized evaluation
    wall_arrays = _walls_to_arrays(walls)

    toolbox.register("individual", init_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluate_individual,
                     sample_points=sample_points,
                     walls=walls,
                     bounds=bounds,
                     num_aps=num_aps,
                     wall_arrays=wall_arrays)
    toolbox.register("mate", tools.cxSimulatedBinaryBounded,
                     low=[min_x + 1.0, min_y + 1.0] * num_aps,
                     up=[max_x - 1.0, max_y - 1.0] * num_aps,
                     eta=15.0)
    toolbox.register("mutate", tools.mutPolynomialBounded,
                     low=[min_x + 1.0, min_y + 1.0] * num_aps,
                     up=[max_x - 1.0, max_y - 1.0] * num_aps,
                     eta=20.0, indpb=1.0 / (2 * num_aps))
    toolbox.register("select", tools.selNSGA2)

    pop = toolbox.population(n=population_size)
    for ind in pop:
        ind.fitness.values = toolbox.evaluate(ind)

    logger.info(f"GA start: num_aps={num_aps}, pop={population_size}, gens={n_generations}")

    for gen in range(n_generations):
        offspring = algorithms.varAnd(pop, toolbox, cxpb=0.9, mutpb=0.2)
        for ind in offspring:
            if not ind.fitness.valid:
                ind.fitness.values = toolbox.evaluate(ind)
        pop = toolbox.select(pop + offspring, k=population_size)

        if progress_cb and (gen % 5 == 0 or gen == n_generations - 1):
            best = min(pop, key=lambda i: i.fitness.values[0])
            best_cov = -best.fitness.values[0] * 100
            progress_cb(gen, best_cov)
            logger.info(f"  gen {gen}: best coverage = {best_cov:.1f}%")

    # Pick the individual with best coverage (objective 0)
    best = min(pop, key=lambda i: i.fitness.values[0])
    best_coverage = -best.fitness.values[0] * 100
    logger.info(f"GA done: best coverage = {best_coverage:.1f}%")

    result = {}
    for i in range(num_aps):
        x = best[i * 2]
        y = best[i * 2 + 1]
        result[f"AP{i + 1}"] = (float(x), float(y), 2.7)
    return result


# ----------------------------------------------------------------------------
# Auto-N search: smallest AP count that hits target coverage
# ----------------------------------------------------------------------------

def capacity_based_min_aps(bounds: Tuple[float, float, float, float],
                           sqm_per_ap: float = 120.0,
                           min_floor: int = 2) -> int:
    """Industry rule of thumb: ~1 enterprise AP per 100-150 m^2.

    Returns at least `min_floor` APs.
    """
    min_x, min_y, max_x, max_y = bounds
    area = max(1.0, (max_x - min_x) * (max_y - min_y))
    return max(min_floor, math.ceil(area / sqm_per_ap))


def optimize_ap_placement_auto(bounds, walls,
                               target_coverage: float = 0.90,
                               min_n: int = 2,
                               max_n: int = 16,
                               sqm_per_ap: float = 120.0,
                               progress_cb=None,
                               **ga_kwargs) -> Tuple[Dict, int, float]:
    """Find min AP count that hits target coverage, respecting capacity rule.

    Logic:
      1. Compute capacity_min = building_area / sqm_per_ap (industry default 120 m^2/AP)
      2. Search N from max(min_n, capacity_min) upward
      3. Return first N that satisfies target_coverage; else best found

    Returns (ap_locations, final_n, final_coverage_pct).
    """
    capacity_min = capacity_based_min_aps(bounds, sqm_per_ap=sqm_per_ap,
                                          min_floor=min_n)
    start_n = max(min_n, capacity_min)
    logger.info(f"Auto-N: capacity_min={capacity_min}, starting at N={start_n}")

    best_result = None
    best_n = start_n
    best_cov = 0.0
    for n in range(start_n, max_n + 1):
        if progress_cb:
            progress_cb(stage=f"Evaluating N={n}", n=n)
        result = optimize_ap_placement(
            bounds=bounds, walls=walls, num_aps=n,
            progress_cb=None, **ga_kwargs,
        )
        cov = _measure_coverage(result, walls, bounds)
        logger.info(f"Auto-N: N={n}, coverage={cov*100:.1f}%")
        if cov > best_cov:
            best_cov = cov
            best_result = result
            best_n = n
        if cov >= target_coverage:
            return result, n, cov
    return best_result, best_n, best_cov


def _measure_coverage(ap_locations, walls, bounds, resolution=25) -> float:
    """Compute coverage % of an AP solution at -65 dBm threshold."""
    min_x, min_y, max_x, max_y = bounds
    xs = np.linspace(min_x + 0.5, max_x - 0.5, resolution)
    ys = np.linspace(min_y + 0.5, max_y - 0.5, resolution)
    aps = [(v[0], v[1]) for v in ap_locations.values()]
    covered = 0
    total = 0
    for x in xs:
        for y in ys:
            best = -100.0
            for ap in aps:
                r = rssi_at_point(ap, (x, y), walls)
                if r > best:
                    best = r
            if best >= COVERAGE_THRESHOLD_DBM:
                covered += 1
            total += 1
    return covered / total if total else 0.0


# ----------------------------------------------------------------------------
# Helper: convert GUI floor plan elements to walls list
# ----------------------------------------------------------------------------

def elements_to_walls(elements) -> List[Dict]:
    """Convert FloorPlanElement objects (or dicts) to walls list for GA."""
    walls = []
    for el in elements:
        etype = getattr(el, 'type', None) or el.get('type')
        if etype not in ('wall', 'obstacle'):
            continue
        points = getattr(el, 'points', None) or el.get('points', [])
        material = getattr(el, 'material', None) or el.get('material', 'concrete')

        # walls are polylines: split into segments
        for i in range(len(points) - 1):
            p1 = tuple(points[i])
            p2 = tuple(points[i + 1])
            walls.append({'p1': p1, 'p2': p2, 'material': material})
    return walls
