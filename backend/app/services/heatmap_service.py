"""Compute wall-aware heatmaps using the GA's signal model."""
import numpy as np

from algorithms.genetic_optimizer import (
    _walls_to_arrays,
    _rssi_vectorized,
    COVERAGE_THRESHOLD_DBM,
)


def compute_heatmap(
    bounds: tuple[float, float, float, float],
    walls: list[dict],
    aps: list[tuple[float, float]],
    resolution: int = 80,
    mode: str = "signal_strength",
) -> dict:
    """Return heatmap grid + statistics ready for JSON serialization.

    Returns:
        {
          'mode': str,
          'bounds': [min_x, min_y, max_x, max_y],
          'resolution': int,
          'grid': 2D list (resolution x resolution),
          'covered_pct': float, 'avg_rssi': float, 'min_rssi': float,
        }
    """
    min_x, min_y, max_x, max_y = bounds
    W1, W2, LOSS = _walls_to_arrays(walls)
    xs = np.linspace(min_x, max_x, resolution)
    ys = np.linspace(min_y, max_y, resolution)
    XX, YY = np.meshgrid(xs, ys)
    sample_points = np.stack([XX.ravel(), YY.ravel()], axis=1)

    if not aps:
        zero = np.full((resolution, resolution), -100.0)
        return _to_dict(zero, zero, bounds, resolution, mode)

    all_rssi = np.full((len(aps), sample_points.shape[0]), -100.0)
    for k, ap in enumerate(aps):
        all_rssi[k] = _rssi_vectorized(ap, sample_points, W1, W2, LOSS)
    all_rssi.sort(axis=0)
    best = all_rssi[-1].reshape(resolution, resolution)
    second = (
        all_rssi[-2].reshape(resolution, resolution)
        if len(aps) > 1 else np.full((resolution, resolution), -100.0)
    )

    return _to_dict(best, second, bounds, resolution, mode)


def _to_dict(best, second, bounds, resolution, mode) -> dict:
    covered_pct = float((best >= COVERAGE_THRESHOLD_DBM).mean() * 100.0)
    avg_rssi = float(best.mean())
    min_rssi = float(best.min())

    if mode == "coverage":
        grid = (best >= COVERAGE_THRESHOLD_DBM).astype(float)
    elif mode == "interference":
        grid = second
    elif mode == "sinr":
        noise_lin = 10 ** (-95 / 10)
        sig_lin = 10 ** (np.clip(best, -100, 0) / 10)
        int_lin = 10 ** (np.clip(second, -100, 0) / 10)
        grid = 10 * np.log10(sig_lin / (int_lin + noise_lin))
    else:
        grid = best

    return {
        "mode": mode,
        "bounds": list(bounds),
        "resolution": resolution,
        "grid": grid.tolist(),
        "covered_pct": covered_pct,
        "avg_rssi": avg_rssi,
        "min_rssi": min_rssi,
    }
