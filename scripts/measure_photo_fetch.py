"""Measure local photo-fetch X for batch sizes 1, 5 and 20.

Run in the deployment environment and set PHOTO_FETCH_X_1/5/20 to the medians.
"""

from __future__ import annotations

import json
import argparse
import random
import statistics
import time

from image_workflow.stickers import PhotoPrefetchPool


def measure(size: int, run: int) -> dict[str, object]:
    pool = PhotoPrefetchPool(size, 300, random.Random(), attempt_limit=size)
    started = time.monotonic()
    pool.start()
    while not pool.download_done.wait(0.1) and time.monotonic() < pool.deadline:
        pass
    elapsed = time.monotonic() - started
    pool.close()
    return {"size": size, "run": run, "seconds": round(elapsed, 3), **pool.stats()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, choices=(1, 5, 20))
    parser.add_argument("--valid-runs", type=int, default=3)
    args = parser.parse_args()
    incomplete = False
    for size in ((args.size,) if args.size else (1, 5, 20)):
        valid = []
        for run in range(1, 7):
            result = measure(size, run)
            print(json.dumps({**result, "errors": [
                error.split(":", 1)[0] for error in result["errors"]
            ]}, ensure_ascii=False), flush=True)
            if result["download_attempts"] == size:
                valid.append(float(result["seconds"]))
            if len(valid) == args.valid_runs:
                break
            time.sleep(2)
        if len(valid) < args.valid_runs:
            print(f"X{size}: 未完成 {args.valid_runs} 次有效测量；不能据此配置等待时间", flush=True)
            incomplete = True
        else:
            label = f"PHOTO_FETCH_X_{size}" if args.valid_runs == 3 else f"本次 X{size} 样本"
            print(f"{label}={statistics.median(valid):.3f}", flush=True)
    if incomplete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
