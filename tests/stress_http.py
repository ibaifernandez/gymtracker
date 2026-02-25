#!/usr/bin/env python3
import argparse
import random
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as tracker


def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return float(values[f])
    return values[f] + (values[c] - values[f]) * (k - f)


def run_one(i):
    started = time.perf_counter()
    op = i % 10
    try:
        with tracker.APP.test_client() as client:
            if op <= 4:
                res = client.get("/api/state?limit=14")
            elif op <= 6:
                res = client.get("/api/state?limit=30")
            elif op == 7:
                day = (i % 28) + 1
                res = client.post(
                    "/api/workout",
                    json={
                        "log_date": f"2026-03-{day:02d}",
                        "session_done_yn": "Y" if i % 2 == 0 else "N",
                        "class_done": f"QA-{i % 7}",
                        "rpe_session": (i % 10) + 1,
                        "notes": f"stress-note-{i},with,comma",
                    },
                )
            else:
                day = (i % 28) + 1
                rnd = random.Random(i)
                res = client.post(
                    "/api/diet",
                    json={
                        "log_date": f"2026-04-{day:02d}",
                        "sleep_hours": round(6.0 + rnd.random() * 3.0, 1),
                        "steps": 7000 + rnd.randint(0, 8000),
                        "weight_kg": round(68.0 + rnd.random() * 6.0, 1),
                        "waist_cm": round(75.0 + rnd.random() * 10.0, 1),
                        "hip_cm": round(92.0 + rnd.random() * 12.0, 1),
                        "creatine_yn": "Y" if i % 3 else "N",
                    },
                )

            elapsed_ms = (time.perf_counter() - started) * 1000.0
            return {"ok": res.status_code == 200, "status": res.status_code, "ms": elapsed_ms, "err": ""}
    except Exception as e:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {"ok": False, "status": 0, "ms": elapsed_ms, "err": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Stress test concurrente in-process para Tracker local."
    )
    parser.add_argument("--total", type=int, default=1200, help="Total de requests.")
    parser.add_argument("--workers", type=int, default=32, help="Concurrencia.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="tracker_stress_") as td:
        td_path = Path(td)
        db_path = td_path / "stress.db"
        uploads = td_path / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)

        orig_db = tracker.DB_PATH
        orig_uploads = tracker.UPLOAD_ROOT
        orig_testing = tracker.APP.config.get("TESTING")

        tracker.DB_PATH = db_path
        tracker.UPLOAD_ROOT = str(uploads)
        tracker.APP.config["TESTING"] = True
        tracker.ensure_schema()

        try:
            started = time.perf_counter()
            results = []
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futs = [ex.submit(run_one, i) for i in range(args.total)]
                for fut in as_completed(futs):
                    results.append(fut.result())
            total_ms = (time.perf_counter() - started) * 1000.0
        finally:
            tracker.DB_PATH = orig_db
            tracker.UPLOAD_ROOT = orig_uploads
            tracker.APP.config["TESTING"] = orig_testing

    latencies = [r["ms"] for r in results]
    failures = [r for r in results if not r["ok"]]
    status_counts = Counter(r["status"] for r in results)

    ok_count = len(results) - len(failures)
    fail_count = len(failures)
    rps = args.total / (total_ms / 1000.0) if total_ms > 0 else 0.0

    print("== Stress Summary ==")
    print(f"total={args.total} workers={args.workers}")
    print(f"ok={ok_count} fail={fail_count} rps={rps:.2f}")
    print(
        "latency_ms "
        f"p50={percentile(latencies, 0.50):.2f} "
        f"p95={percentile(latencies, 0.95):.2f} "
        f"p99={percentile(latencies, 0.99):.2f} "
        f"max={max(latencies) if latencies else 0.0:.2f}"
    )
    print("status_counts=", dict(sorted(status_counts.items(), key=lambda kv: kv[0])))

    if failures:
        print("sample_failures:")
        for row in failures[:10]:
            print(f"- status={row['status']} err={row['err']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
