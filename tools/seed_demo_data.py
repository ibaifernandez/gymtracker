#!/usr/bin/env python3
"""Populate tracker.db with coherent demo data for UX/QA checks.

Usage examples:
  python3 tools/seed_demo_data.py --days 45 --profile fatloss
  python3 tools/seed_demo_data.py --reset-all --purge-future --days 60 --profile recomp
  python3 tools/seed_demo_data.py --reset-all --purge-future --days 90 --diet-only --random-profile --random-seed
"""

from __future__ import annotations

import argparse
import os
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path(
    os.environ.get("TRACKER_DB_PATH", str(BASE_DIR / "tracker.db"))
).expanduser()


@dataclass(frozen=True)
class Profile:
    weight_start: float
    weight_drift: float
    waist_start: float
    waist_drift: float
    hip_start: float
    hip_drift: float
    steps_base: int
    sleep_base: float
    workout_gain: float


PROFILES = {
    "fatloss": Profile(
        weight_start=76.0,
        weight_drift=-0.035,
        waist_start=86.5,
        waist_drift=-0.05,
        hip_start=98.2,
        hip_drift=-0.01,
        steps_base=10800,
        sleep_base=7.3,
        workout_gain=0.25,
    ),
    "recomp": Profile(
        weight_start=74.2,
        weight_drift=0.006,
        waist_start=84.2,
        waist_drift=-0.028,
        hip_start=97.8,
        hip_drift=0.006,
        steps_base=9800,
        sleep_base=7.2,
        workout_gain=0.45,
    ),
    "gain": Profile(
        weight_start=72.6,
        weight_drift=0.03,
        waist_start=82.8,
        waist_drift=0.012,
        hip_start=96.6,
        hip_drift=0.01,
        steps_base=9000,
        sleep_base=7.0,
        workout_gain=0.6,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate tracker.db with synthetic but coherent diet/workout history."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"SQLite file path (default: {DEFAULT_DB})",
    )
    parser.add_argument("--days", type=int, default=45, help="Number of days to generate.")
    parser.add_argument(
        "--end-date",
        default=date.today().isoformat(),
        help="Last date in YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default="fatloss",
        help="Trend profile used to shape generated data.",
    )
    parser.add_argument(
        "--random-profile",
        action="store_true",
        help="Pick a random profile each run.",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducible output."
    )
    parser.add_argument(
        "--random-seed",
        action="store_true",
        help="Use a fresh random seed each run.",
    )
    parser.add_argument(
        "--photo-every",
        type=int,
        default=0,
        help="Mark photo_yn='Y' every N days (0 disables).",
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Delete all rows in diet_log, workout_log, photo_log before generating.",
    )
    parser.add_argument(
        "--reset-range",
        action="store_true",
        help="Delete existing rows only in the target date range before generating.",
    )
    parser.add_argument(
        "--purge-future",
        action="store_true",
        help="Delete rows after end-date (useful after QA runs with future dates).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing to DB.",
    )
    parser.add_argument(
        "--diet-only",
        action="store_true",
        help="Generate only check-ins (diet_log + photo_yn), skipping workout/session rows.",
    )
    return parser.parse_args()


def valid_iso_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def daterange(start_date: date, end_date: date) -> Iterable[date]:
    cursor = start_date
    while cursor <= end_date:
        yield cursor
        cursor += timedelta(days=1)


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r[1] == column for r in rows)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS diet_log (
          log_date TEXT PRIMARY KEY,
          sleep_hours REAL,
          sleep_quality INTEGER,
          steps INTEGER,
          weight_kg REAL,
          waist_cm REAL,
          hip_cm REAL,
          alcohol_units INTEGER DEFAULT 0,
          creatine_yn TEXT,
          photo_yn TEXT
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_diet_log_date ON diet_log(log_date);")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_log (
          log_date TEXT PRIMARY KEY,
          session_done_yn TEXT,
          class_done TEXT,
          rpe_session INTEGER,
          hipthrust_topset TEXT,
          squat_topset TEXT,
          notes TEXT
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workout_log_date ON workout_log(log_date);")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_session (
          session_id INTEGER PRIMARY KEY AUTOINCREMENT,
          log_date TEXT NOT NULL,
          session_order INTEGER NOT NULL DEFAULT 1,
          session_done_yn TEXT,
          session_type TEXT,
          class_done TEXT,
          rpe_session INTEGER,
          notes TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
          UNIQUE(log_date, session_order)
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_exercise (
          exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
          session_id INTEGER NOT NULL,
          exercise_name TEXT NOT NULL,
          set_order INTEGER NOT NULL DEFAULT 1,
          weight_kg REAL,
          reps INTEGER,
          rpe REAL,
          topset_text TEXT,
          FOREIGN KEY(session_id) REFERENCES workout_session(session_id) ON DELETE CASCADE
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workout_session_date ON workout_session(log_date);")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workout_exercise_session ON workout_exercise(session_id, set_order);"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS photo_log (
          log_date TEXT NOT NULL,
          kind TEXT NOT NULL,
          path TEXT NOT NULL,
          original_name TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
          PRIMARY KEY (log_date, kind)
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_photo_date ON photo_log(log_date);")

    # Workout structured columns (v0.0.1.0+)
    if not has_column(conn, "workout_log", "session_type"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN session_type TEXT;")
    if not has_column(conn, "workout_log", "hipthrust_weight_kg"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN hipthrust_weight_kg REAL;")
    if not has_column(conn, "workout_log", "hipthrust_reps"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN hipthrust_reps INTEGER;")
    if not has_column(conn, "workout_log", "hipthrust_rpe"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN hipthrust_rpe REAL;")
    if not has_column(conn, "workout_log", "squat_weight_kg"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN squat_weight_kg REAL;")
    if not has_column(conn, "workout_log", "squat_reps"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN squat_reps INTEGER;")
    if not has_column(conn, "workout_log", "squat_rpe"):
        conn.execute("ALTER TABLE workout_log ADD COLUMN squat_rpe REAL;")
    conn.execute(
        "UPDATE workout_log SET session_type = COALESCE(NULLIF(session_type, ''), 'clase');"
    )
    conn.commit()


def fmt_topset(weight: float | None, reps: int | None, rpe: float | None) -> str | None:
    if weight is None and reps is None and rpe is None:
        return None
    parts: list[str] = []
    if weight is not None:
        parts.append(f"{weight:g}kg")
    if reps is not None:
        parts.append(f"{reps} reps")
    if rpe is not None:
        parts.append(f"RPE {rpe:g}")
    return " · ".join(parts) if parts else None


def main() -> int:
    args = parse_args()

    if args.days < 1:
        raise SystemExit("--days must be >= 1")
    if not valid_iso_date(args.end_date):
        raise SystemExit("--end-date must be YYYY-MM-DD")

    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=args.days - 1)
    selected_profile_name = (
        random.SystemRandom().choice(sorted(PROFILES.keys()))
        if args.random_profile
        else args.profile
    )
    selected_seed = (
        random.SystemRandom().randint(1, 999_999_999)
        if args.random_seed
        else args.seed
    )
    profile = PROFILES[selected_profile_name]
    rng = random.Random(selected_seed)

    db_path = args.db.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("[dry-run] no DB changes will be written")
        print(f"db={db_path}")
        print(f"range={start_date.isoformat()}..{end_date.isoformat()} ({args.days} days)")
        print(f"profile={selected_profile_name}, seed={selected_seed}")
        print(f"diet_only={bool(args.diet_only)}")
        if args.reset_all:
            print("[dry-run] would reset all logs")
        if args.reset_range:
            print("[dry-run] would reset only target range")
        if args.purge_future:
            print(f"[dry-run] would purge records with log_date > {end_date.isoformat()}")
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    if args.reset_all:
        conn.execute("DELETE FROM workout_exercise;")
        conn.execute("DELETE FROM workout_session;")
        conn.execute("DELETE FROM photo_log;")
        conn.execute("DELETE FROM workout_log;")
        conn.execute("DELETE FROM diet_log;")
    elif args.reset_range:
        conn.execute(
            """
            DELETE FROM workout_exercise
            WHERE session_id IN (
              SELECT session_id FROM workout_session WHERE log_date BETWEEN ? AND ?
            );
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        conn.execute(
            "DELETE FROM workout_session WHERE log_date BETWEEN ? AND ?;",
            (start_date.isoformat(), end_date.isoformat()),
        )
        conn.execute(
            "DELETE FROM photo_log WHERE log_date BETWEEN ? AND ?;",
            (start_date.isoformat(), end_date.isoformat()),
        )
        conn.execute(
            "DELETE FROM workout_log WHERE log_date BETWEEN ? AND ?;",
            (start_date.isoformat(), end_date.isoformat()),
        )
        conn.execute(
            "DELETE FROM diet_log WHERE log_date BETWEEN ? AND ?;",
            (start_date.isoformat(), end_date.isoformat()),
        )

    if args.purge_future:
        conn.execute(
            """
            DELETE FROM workout_exercise
            WHERE session_id IN (
              SELECT session_id FROM workout_session WHERE log_date > ?
            );
            """,
            (end_date.isoformat(),),
        )
        conn.execute("DELETE FROM workout_session WHERE log_date > ?;", (end_date.isoformat(),))
        conn.execute("DELETE FROM photo_log WHERE log_date > ?;", (end_date.isoformat(),))
        conn.execute("DELETE FROM workout_log WHERE log_date > ?;", (end_date.isoformat(),))
        conn.execute("DELETE FROM diet_log WHERE log_date > ?;", (end_date.isoformat(),))

    existing_diet = {
        r["log_date"]
        for r in conn.execute(
            "SELECT log_date FROM diet_log WHERE log_date BETWEEN ? AND ?;",
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    }
    existing_workout = {}
    if not args.diet_only:
        for r in conn.execute(
            """
            SELECT session_id, log_date, session_order
            FROM workout_session
            WHERE log_date BETWEEN ? AND ?
            ORDER BY log_date ASC, session_order ASC;
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall():
            if r["log_date"] not in existing_workout:
                existing_workout[r["log_date"]] = r["session_id"]

    diet_inserted = 0
    diet_updated = 0
    workout_inserted = 0
    workout_updated = 0

    ht_weight_prog = 95.0
    sq_weight_prog = 75.0
    class_options = [
        "Pilates",
        "Movilidad",
        "Crossfit",
        "Yoga",
        "Cardio Z2",
        "HIIT",
    ]
    note_options = [
        "Buena sesion, tecnica estable.",
        "Algo de fatiga al final.",
        "Dormi peor, ajuste de carga.",
        "Sesion solida.",
        "Recuperacion activa.",
    ]

    for idx, current in enumerate(daterange(start_date, end_date)):
        log_date = current.isoformat()
        is_weekend = current.weekday() >= 5

        sleep_hours = clamp(
            rng.gauss(profile.sleep_base + (0.25 if is_weekend else -0.05), 0.35),
            5.4,
            9.2,
        )
        sleep_quality = int(
            round(clamp(5.0 + (sleep_hours - 6.6) * 1.5 + rng.gauss(0, 1.0), 1, 10))
        )
        steps = int(
            round(
                clamp(
                    rng.gauss(profile.steps_base + (900 if is_weekend else 0), 1450),
                    3500,
                    21000,
                )
            )
        )

        weight_kg = round(
            clamp(
                profile.weight_start + profile.weight_drift * idx + rng.gauss(0, 0.18),
                45,
                180,
            ),
            1,
        )
        waist_cm = round(
            clamp(
                profile.waist_start + profile.waist_drift * idx + rng.gauss(0, 0.22),
                55,
                160,
            ),
            1,
        )
        hip_cm = round(
            clamp(profile.hip_start + profile.hip_drift * idx + rng.gauss(0, 0.18), 65, 180),
            1,
        )
        if hip_cm <= waist_cm:
            hip_cm = round(waist_cm + 8.5 + abs(rng.gauss(0, 0.7)), 1)

        alcohol_units = 0 if not is_weekend else (1 if rng.random() < 0.35 else 0)
        creatine_yn = "Y" if rng.random() < 0.86 else "N"
        photo_yn = (
            "Y"
            if args.photo_every > 0 and ((idx + 1) % args.photo_every == 0)
            else "N"
        )

        conn.execute(
            """
            INSERT INTO diet_log (
              log_date, sleep_hours, sleep_quality, steps, weight_kg,
              waist_cm, hip_cm, alcohol_units, creatine_yn, photo_yn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(log_date) DO UPDATE SET
              sleep_hours=excluded.sleep_hours,
              sleep_quality=excluded.sleep_quality,
              steps=excluded.steps,
              weight_kg=excluded.weight_kg,
              waist_cm=excluded.waist_cm,
              hip_cm=excluded.hip_cm,
              alcohol_units=excluded.alcohol_units,
              creatine_yn=excluded.creatine_yn,
              photo_yn=excluded.photo_yn;
            """,
            (
                log_date,
                round(sleep_hours, 1),
                sleep_quality,
                steps,
                weight_kg,
                waist_cm,
                hip_cm,
                alcohol_units,
                creatine_yn,
                photo_yn,
            ),
        )

        if log_date in existing_diet:
            diet_updated += 1
        else:
            diet_inserted += 1
            existing_diet.add(log_date)

        if args.diet_only:
            continue

        # 4 training sessions/week baseline: Mon, Wed, Fri, Sat
        if current.weekday() not in {0, 2, 4, 5}:
            continue

        session_done_yn = "N" if rng.random() < 0.08 else "Y"
        session_type = rng.choices(
            population=["pesas", "mixta", "clase"],
            weights=[0.52, 0.28, 0.20],
            k=1,
        )[0]
        class_done = None
        rpe_session = int(round(clamp(rng.gauss(7.5, 1.0), 4, 10)))
        hip_weight = None
        hip_reps = None
        hip_rpe = None
        sq_weight_val = None
        sq_reps = None
        sq_rpe = None

        if session_done_yn == "Y":
            if session_type in ("clase", "mixta"):
                class_done = rng.choice(class_options)

            if session_type in ("pesas", "mixta"):
                ht_weight_prog += profile.workout_gain + rng.choice([0, 0, 0.5, 1.0]) - 0.1
                sq_weight_prog += profile.workout_gain * 0.9 + rng.choice([0, 0, 0.5]) - 0.1

                hip_weight = round(clamp(ht_weight_prog, 40, 260), 1)
                hip_reps = int(clamp(round(rng.gauss(7.2, 1.4)), 3, 15))
                hip_rpe = round(clamp(rng.gauss(8.0, 0.7), 5, 10), 1)
                sq_weight_val = round(clamp(sq_weight_prog, 30, 240), 1)
                sq_reps = int(clamp(round(rng.gauss(6.8, 1.5)), 3, 15))
                sq_rpe = round(clamp(rng.gauss(7.8, 0.8), 5, 10), 1)
        else:
            class_done = "Descanso / recuperacion"
            session_type = "clase"

        hip_topset = fmt_topset(hip_weight, hip_reps, hip_rpe)
        sq_topset = fmt_topset(sq_weight_val, sq_reps, sq_rpe)
        notes = rng.choice(note_options) if session_done_yn == "Y" else "Sesion no completada."

        if log_date in existing_workout:
            session_id = existing_workout[log_date]
            conn.execute(
                """
                UPDATE workout_session
                SET
                  session_done_yn = ?,
                  class_done = ?,
                  rpe_session = ?,
                  session_type = ?,
                  notes = ?,
                  updated_at = ?
                WHERE session_id = ?;
                """,
                (
                    session_done_yn,
                    class_done,
                    rpe_session,
                    session_type,
                    notes,
                    datetime.now().replace(microsecond=0).isoformat(),
                    session_id,
                ),
            )
            conn.execute("DELETE FROM workout_exercise WHERE session_id = ?;", (session_id,))
            workout_updated += 1
        else:
            next_order = conn.execute(
                "SELECT COALESCE(MAX(session_order), 0) + 1 AS next_order FROM workout_session WHERE log_date = ?;",
                (log_date,),
            ).fetchone()["next_order"]
            cur = conn.execute(
                """
                INSERT INTO workout_session (
                  log_date, session_order, session_done_yn, session_type,
                  class_done, rpe_session, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    log_date,
                    next_order,
                    session_done_yn,
                    session_type,
                    class_done,
                    rpe_session,
                    notes,
                    datetime.now().replace(microsecond=0).isoformat(),
                    datetime.now().replace(microsecond=0).isoformat(),
                ),
            )
            session_id = cur.lastrowid
            existing_workout[log_date] = session_id
            workout_inserted += 1

        ex_rows = []
        if session_type in ("pesas", "mixta"):
            if hip_weight is not None or hip_reps is not None or hip_rpe is not None or hip_topset:
                ex_rows.append(("Hip Thrust", hip_weight, hip_reps, hip_rpe, hip_topset))
            if sq_weight_val is not None or sq_reps is not None or sq_rpe is not None or sq_topset:
                ex_rows.append(("Sentadilla", sq_weight_val, sq_reps, sq_rpe, sq_topset))
        for ex_idx, ex in enumerate(ex_rows, start=1):
            conn.execute(
                """
                INSERT INTO workout_exercise (
                  session_id, exercise_name, set_order, weight_kg, reps, rpe, topset_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session_id,
                    ex[0],
                    ex_idx,
                    ex[1],
                    ex[2],
                    ex[3],
                    ex[4],
                ),
            )

    conn.commit()

    total_diet = conn.execute("SELECT COUNT(*) AS n FROM diet_log;").fetchone()["n"]
    total_workout = conn.execute("SELECT COUNT(*) AS n FROM workout_session;").fetchone()["n"]
    last7 = conn.execute(
        """
        SELECT log_date, weight_kg, waist_cm, hip_cm
        FROM diet_log
        ORDER BY log_date DESC
        LIMIT 7;
        """
    ).fetchall()
    conn.close()

    last7 = list(reversed(last7))
    weight_delta = None
    whr_delta = None
    if len(last7) >= 2 and last7[0]["weight_kg"] is not None and last7[-1]["weight_kg"] is not None:
        weight_delta = float(last7[-1]["weight_kg"]) - float(last7[0]["weight_kg"])
    if len(last7) >= 2:
        try:
            first_whr = float(last7[0]["waist_cm"]) / float(last7[0]["hip_cm"])
            last_whr = float(last7[-1]["waist_cm"]) / float(last7[-1]["hip_cm"])
            whr_delta = last_whr - first_whr
        except Exception:
            whr_delta = None

    print(f"Seed completed on {db_path}")
    print(f"Date range: {start_date.isoformat()} .. {end_date.isoformat()} ({args.days} days)")
    print(f"Profile: {selected_profile_name} | Seed: {selected_seed}")
    print(f"Diet rows   -> inserted: {diet_inserted}, updated: {diet_updated}, total: {total_diet}")
    print(
        "Workout rows-> inserted: "
        f"{workout_inserted}, updated: {workout_updated}, total: {total_workout}"
    )
    if args.diet_only:
        print("Mode: diet-only (sin registros de entreno).")
    if weight_delta is not None:
        print(f"Last 7 records weight delta: {weight_delta:+.2f} kg")
    if whr_delta is not None:
        print(f"Last 7 records WHR delta: {whr_delta:+.3f}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
