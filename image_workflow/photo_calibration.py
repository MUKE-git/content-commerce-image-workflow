"""Measured acquisition baselines; override these in the deployment environment."""

from __future__ import annotations

import os


# Local medians of three valid trials per size, measured with this pipeline.
LOCAL_BASELINE_SECONDS = {1: 30.656, 5: 44.722, 20: 96.892}


def _baseline(size: int) -> float:
    return float(os.environ.get(f"PHOTO_FETCH_X_{size}", LOCAL_BASELINE_SECONDS[size]))


def online_wait_seconds(count: int) -> float:
    """2X batch deadline, interpolated between measured 1/5/20-image baselines."""
    if not 1 <= count <= 20:
        raise ValueError("每批需上传 1 至 20 张图片")
    low, high = (1, 5) if count <= 5 else (5, 20)
    x = _baseline(low) + (_baseline(high) - _baseline(low)) * (count - low) / (high - low)
    if x < 0:
        raise ValueError("照片取图基准时间不能为负数")
    return 2 * x
