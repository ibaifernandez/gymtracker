#!/usr/bin/env python3
"""Clear tracker data tables.

Usage:
  python3 tools/clear_data.py
  python3 tools/clear_data.py --db /path/to/tracker.db
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path(
    os.environ.get("TRACKER_DB_PATH", str(BASE_DIR / "tracker.db"))
).expanduser()
UPLOAD_ROOT = Path(
    os.environ.get("TRACKER_UPLOAD_ROOT", str(BASE_DIR / "static" / "uploads"))
).expanduser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete all log rows from tracker DB.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"SQLite file path (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--vacuum",
        action="store_true",
        help="Run VACUUM after deletion to compact DB file.",
    )
    return parser.parse_args()


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1;",
        (table,),
    ).fetchone()
    return row is not None


def main() -> int:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    def count_or_none(table: str):
        if not table_exists(conn, table):
            return None
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table};").fetchone()["n"]

    data_tables = (
        # Registro real
        "workout_exercise",
        "workout_session",
        "workout_log",
        "photo_log",
        "diet_log",
        # Suplementos
        "supplement_daily_log",
        "supplement_catalog",
        # Plan diario
        "plan_day_adherence",
        "plan_day_workout_exercise",
        "plan_day_workout_session",
        "plan_day_diet",
    )

    before = {table: count_or_none(table) for table in data_tables}

    for table in data_tables:
        if table_exists(conn, table):
            conn.execute(f"DELETE FROM {table};")

    conn.commit()

    if args.vacuum:
        conn.execute("VACUUM;")

    after = {table: count_or_none(table) for table in data_tables}

    conn.close()

    upload_deleted = 0
    if UPLOAD_ROOT.exists():
        upload_deleted = sum(1 for p in UPLOAD_ROOT.rglob("*") if p.is_file())
        shutil.rmtree(UPLOAD_ROOT)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"Clear completed on {db_path}")
    print("Before ->")
    for table in data_tables:
        print(f"  {table}: {before[table]}")
    print("After  ->")
    for table in data_tables:
        print(f"  {table}: {after[table]}")
    print(f"Uploads-> deleted files: {upload_deleted}, folder: {UPLOAD_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
