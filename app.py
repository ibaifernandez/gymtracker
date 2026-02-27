import os
import re
import csv
import hmac
import json
import secrets
import shutil
import sqlite3
import unicodedata
import zipfile
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import closing, contextmanager
from tempfile import TemporaryDirectory

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except Exception:  # pragma: no cover - entorno sin Pillow
    Image = None
    ImageOps = None

    class UnidentifiedImageError(Exception):
        pass


APP = Flask(__name__, template_folder="templates", static_folder="static")
APP.config["JSON_SORT_KEYS"] = False
APP.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB máximo por request
APP.secret_key = os.environ.get("TRACKER_SECRET_KEY") or secrets.token_hex(32)
APP.config["SESSION_COOKIE_HTTPONLY"] = True
APP.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(
    os.environ.get("TRACKER_DB_PATH", str(BASE_DIR / "tracker.db"))
).expanduser()
PLAN_WORKOUT_GUIDED_TEMPLATE_PATH = BASE_DIR / "docs" / "plan_workout_template_guided.csv"
PLAN_CSV_AI_SYSTEM_PROMPT_PATH = BASE_DIR / "docs" / "PLAN_CSV_AI_SYSTEM_PROMPT.md"
PLAN_CSV_AI_INSTRUCTIONS_LEGACY_PATH = BASE_DIR / "docs" / "PLAN_CSV_AI_INSTRUCTIONS.md"
PLAN_CSV_AI_INSTRUCTIONS_DIET_PATH = BASE_DIR / "docs" / "PLAN_CSV_AI_INSTRUCTIONS_DIET.md"
PLAN_CSV_AI_INSTRUCTIONS_WORKOUT_PATH = BASE_DIR / "docs" / "PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md"

UPLOAD_ROOT = str(
    Path(
        os.environ.get("TRACKER_UPLOAD_ROOT", os.path.join(APP.root_path, "static", "uploads"))
    ).expanduser()
)
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
SUMMARY_WINDOW_CHOICES = (7, 15, 30, 60, 90)
PLAN_ADHERENCE_WINDOW_CHOICES = (7, 15, 30)
CSRF_SESSION_KEY = "csrf_token"


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "on")


def _int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        val = int(str(raw).strip())
    except Exception:
        return default
    return max(min_value, min(max_value, val))


def _load_auth_hash() -> str:
    stored = (os.environ.get("TRACKER_AUTH_PASSWORD_HASH") or "").strip()
    if stored:
        return stored
    plain = os.environ.get("TRACKER_AUTH_PASSWORD")
    if plain:
        return generate_password_hash(plain)
    return ""


AUTH_PASSWORD_HASH = _load_auth_hash()
AUTH_ENABLED = _bool_env("TRACKER_AUTH_ENABLED", default=bool(AUTH_PASSWORD_HASH))

PHOTO_COMPRESSION_ENABLED = _bool_env("TRACKER_PHOTO_COMPRESSION_ENABLED", default=True)
PHOTO_MAX_SIDE = _int_env("TRACKER_PHOTO_MAX_SIDE", default=1600, min_value=640, max_value=4096)
PHOTO_QUALITY = _int_env("TRACKER_PHOTO_QUALITY", default=82, min_value=50, max_value=95)
PHOTO_PREFER_WEBP = _bool_env("TRACKER_PHOTO_PREFER_WEBP", default=True)
PILLOW_AVAILABLE = Image is not None and ImageOps is not None


def static_asset_version(filename: str) -> str:
    try:
        return str(int((BASE_DIR / "static" / filename).stat().st_mtime))
    except Exception:
        return "1"


@APP.context_processor
def inject_asset_versions():
    return {
        "asset_v_css": static_asset_version("styles.css"),
        "asset_v_app_js": static_asset_version("app.js"),
        "asset_v_login_js": static_asset_version("login.js"),
        "asset_v_cover_css": static_asset_version("cover.css"),
    }


# -----------------------------
# DB helpers
# -----------------------------
@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    try:
        yield conn
    finally:
        conn.close()


def has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return any(r["name"] == column for r in rows)


def table_exists(conn, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1;",
        (table,),
    ).fetchone()
    return row is not None


def ensure_schema():
    with _conn() as conn:
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_workout_log_date ON workout_log(log_date);"
        )
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_workout_session_date ON workout_session(log_date);"
        )
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

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS supplement_catalog (
              supplement_id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              doses_per_day INTEGER NOT NULL DEFAULT 1,
              active_yn TEXT NOT NULL DEFAULT 'Y',
              notes TEXT,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
            );
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_supplement_catalog_name_ci ON supplement_catalog(name COLLATE NOCASE);"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS supplement_daily_log (
              log_date TEXT NOT NULL,
              supplement_id INTEGER NOT NULL,
              doses_taken INTEGER NOT NULL DEFAULT 0,
              notes TEXT,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              PRIMARY KEY (log_date, supplement_id),
              FOREIGN KEY(supplement_id) REFERENCES supplement_catalog(supplement_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_supplement_daily_date ON supplement_daily_log(log_date);"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_day_diet (
              log_date TEXT PRIMARY KEY,
              calories_target_kcal REAL,
              protein_target_g REAL,
              carbs_target_g REAL,
              fat_target_g REAL,
              breakfast TEXT,
              snack_1 TEXT,
              lunch TEXT,
              snack_2 TEXT,
              dinner TEXT,
              notes TEXT,
              source_tag TEXT,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_day_workout_session (
              log_date TEXT NOT NULL,
              plan_session_id TEXT NOT NULL,
              session_type TEXT NOT NULL DEFAULT 'clase',
              warmup TEXT,
              class_sessions TEXT,
              cardio TEXT,
              mobility_cooldown TEXT,
              additional_exercises TEXT,
              notes TEXT,
              source_tag TEXT,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              PRIMARY KEY(log_date, plan_session_id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_day_workout_exercise (
              log_date TEXT NOT NULL,
              plan_session_id TEXT NOT NULL,
              exercise_order INTEGER NOT NULL DEFAULT 1,
              exercise_name TEXT NOT NULL,
              target_sets INTEGER,
              target_reps_min INTEGER,
              target_reps_max INTEGER,
              target_weight_kg REAL,
              target_rpe REAL,
              intensity_target TEXT,
              progression_weight_rule TEXT,
              progression_reps_rule TEXT,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              PRIMARY KEY(log_date, plan_session_id, exercise_order),
              FOREIGN KEY(log_date, plan_session_id)
                REFERENCES plan_day_workout_session(log_date, plan_session_id)
                ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_day_adherence (
              log_date TEXT PRIMARY KEY,
              diet_score REAL,
              workout_score REAL,
              notes TEXT,
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_diet_date ON plan_day_diet(log_date);")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plan_workout_session_date ON plan_day_workout_session(log_date);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plan_workout_exercise_date ON plan_day_workout_exercise(log_date, plan_session_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plan_adherence_date ON plan_day_adherence(log_date);"
        )

        # Migración suave para DB existentes
        if not has_column(conn, "photo_log", "original_name"):
            conn.execute("ALTER TABLE photo_log ADD COLUMN original_name TEXT;")
        if not has_column(conn, "photo_log", "created_at"):
            conn.execute("ALTER TABLE photo_log ADD COLUMN created_at TEXT;")
        conn.execute(
            "UPDATE photo_log SET created_at = COALESCE(NULLIF(created_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));"
        )

        if not has_column(conn, "supplement_catalog", "active_yn"):
            conn.execute("ALTER TABLE supplement_catalog ADD COLUMN active_yn TEXT;")
        if not has_column(conn, "supplement_catalog", "notes"):
            conn.execute("ALTER TABLE supplement_catalog ADD COLUMN notes TEXT;")
        if not has_column(conn, "supplement_catalog", "created_at"):
            conn.execute("ALTER TABLE supplement_catalog ADD COLUMN created_at TEXT;")
        if not has_column(conn, "supplement_catalog", "updated_at"):
            conn.execute("ALTER TABLE supplement_catalog ADD COLUMN updated_at TEXT;")
        conn.execute(
            """
            UPDATE supplement_catalog
            SET
              doses_per_day = CASE
                WHEN doses_per_day IS NULL OR doses_per_day < 1 THEN 1
                ELSE doses_per_day
              END,
              active_yn = CASE
                WHEN UPPER(COALESCE(active_yn, 'Y')) = 'N' THEN 'N'
                ELSE 'Y'
              END,
              created_at = COALESCE(NULLIF(created_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at = COALESCE(NULLIF(updated_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));
            """
        )

        if not has_column(conn, "supplement_daily_log", "doses_taken"):
            conn.execute("ALTER TABLE supplement_daily_log ADD COLUMN doses_taken INTEGER;")
        if not has_column(conn, "supplement_daily_log", "notes"):
            conn.execute("ALTER TABLE supplement_daily_log ADD COLUMN notes TEXT;")
        if not has_column(conn, "supplement_daily_log", "created_at"):
            conn.execute("ALTER TABLE supplement_daily_log ADD COLUMN created_at TEXT;")
        if not has_column(conn, "supplement_daily_log", "updated_at"):
            conn.execute("ALTER TABLE supplement_daily_log ADD COLUMN updated_at TEXT;")
        conn.execute(
            """
            UPDATE supplement_daily_log
            SET
              doses_taken = CASE
                WHEN doses_taken IS NULL OR doses_taken < 0 THEN 0
                ELSE doses_taken
              END,
              created_at = COALESCE(NULLIF(created_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at = COALESCE(NULLIF(updated_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));
            """
        )

        if not has_column(conn, "plan_day_diet", "notes"):
            conn.execute("ALTER TABLE plan_day_diet ADD COLUMN notes TEXT;")
        if not has_column(conn, "plan_day_diet", "source_tag"):
            conn.execute("ALTER TABLE plan_day_diet ADD COLUMN source_tag TEXT;")
        if not has_column(conn, "plan_day_diet", "created_at"):
            conn.execute("ALTER TABLE plan_day_diet ADD COLUMN created_at TEXT;")
        if not has_column(conn, "plan_day_diet", "updated_at"):
            conn.execute("ALTER TABLE plan_day_diet ADD COLUMN updated_at TEXT;")
        conn.execute(
            """
            UPDATE plan_day_diet
            SET
              created_at = COALESCE(NULLIF(created_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at = COALESCE(NULLIF(updated_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));
            """
        )

        if not has_column(conn, "plan_day_workout_session", "class_sessions"):
            conn.execute("ALTER TABLE plan_day_workout_session ADD COLUMN class_sessions TEXT;")
        if not has_column(conn, "plan_day_workout_session", "additional_exercises"):
            conn.execute("ALTER TABLE plan_day_workout_session ADD COLUMN additional_exercises TEXT;")
        if not has_column(conn, "plan_day_workout_session", "source_tag"):
            conn.execute("ALTER TABLE plan_day_workout_session ADD COLUMN source_tag TEXT;")
        if not has_column(conn, "plan_day_workout_session", "created_at"):
            conn.execute("ALTER TABLE plan_day_workout_session ADD COLUMN created_at TEXT;")
        if not has_column(conn, "plan_day_workout_session", "updated_at"):
            conn.execute("ALTER TABLE plan_day_workout_session ADD COLUMN updated_at TEXT;")
        conn.execute(
            """
            UPDATE plan_day_workout_session
            SET
              session_type = CASE
                WHEN LOWER(COALESCE(session_type, '')) = 'mixta'
                  THEN 'pesas'
                WHEN LOWER(COALESCE(session_type, '')) IN ('pesas', 'clase')
                  THEN LOWER(session_type)
                ELSE 'clase'
              END,
              created_at = COALESCE(NULLIF(created_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at = COALESCE(NULLIF(updated_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));
            """
        )

        if not has_column(conn, "plan_day_workout_exercise", "target_sets"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN target_sets INTEGER;")
        if not has_column(conn, "plan_day_workout_exercise", "target_reps_min"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN target_reps_min INTEGER;")
        if not has_column(conn, "plan_day_workout_exercise", "target_reps_max"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN target_reps_max INTEGER;")
        if not has_column(conn, "plan_day_workout_exercise", "target_weight_kg"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN target_weight_kg REAL;")
        if not has_column(conn, "plan_day_workout_exercise", "target_rpe"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN target_rpe REAL;")
        if not has_column(conn, "plan_day_workout_exercise", "intensity_target"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN intensity_target TEXT;")
        if not has_column(conn, "plan_day_workout_exercise", "progression_weight_rule"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN progression_weight_rule TEXT;")
        if not has_column(conn, "plan_day_workout_exercise", "progression_reps_rule"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN progression_reps_rule TEXT;")
        if not has_column(conn, "plan_day_workout_exercise", "created_at"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN created_at TEXT;")
        if not has_column(conn, "plan_day_workout_exercise", "updated_at"):
            conn.execute("ALTER TABLE plan_day_workout_exercise ADD COLUMN updated_at TEXT;")
        conn.execute(
            """
            UPDATE plan_day_workout_exercise
            SET
              created_at = COALESCE(NULLIF(created_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              updated_at = COALESCE(NULLIF(updated_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));
            """
        )

        if not has_column(conn, "plan_day_adherence", "updated_at"):
            conn.execute("ALTER TABLE plan_day_adherence ADD COLUMN updated_at TEXT;")
        if not has_column(conn, "plan_day_adherence", "notes"):
            conn.execute("ALTER TABLE plan_day_adherence ADD COLUMN notes TEXT;")
        conn.execute(
            """
            UPDATE plan_day_adherence
            SET
              updated_at = COALESCE(NULLIF(updated_at, ''), strftime('%Y-%m-%dT%H:%M:%S', 'now'));
            """
        )

        # Evolucion de workout_log (v0.0.1.0): modo clase/pesas + sets estructurados
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
        conn.execute(
            """
            UPDATE workout_log
            SET session_type = CASE
              WHEN LOWER(COALESCE(session_type, '')) = 'mixta' THEN 'pesas'
              WHEN LOWER(COALESCE(session_type, '')) IN ('clase', 'pesas') THEN LOWER(session_type)
              ELSE 'clase'
            END;
            """
        )
        conn.execute(
            """
            UPDATE workout_session
            SET session_type = CASE
              WHEN LOWER(COALESCE(session_type, '')) = 'mixta' THEN 'pesas'
              WHEN LOWER(COALESCE(session_type, '')) IN ('clase', 'pesas') THEN LOWER(session_type)
              ELSE 'clase'
            END;
            """
        )

        # Migracion legacy workout_log -> workout_session/workout_exercise
        try:
            current_sessions = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_session;"
            ).fetchone()["n"]
            if table_exists(conn, "workout_log") and current_sessions == 0:
                def _legacy_topset(weight, reps, rpe):
                    if weight is None and reps is None and rpe is None:
                        return None
                    parts = []
                    if weight is not None:
                        parts.append(f"{weight:g}kg")
                    if reps is not None:
                        parts.append(f"{reps} reps")
                    if rpe is not None:
                        parts.append(f"RPE {rpe:g}")
                    return " · ".join(parts) if parts else None

                legacy_rows = conn.execute(
                    """
                    SELECT
                      log_date, session_done_yn, class_done, rpe_session, session_type,
                      hipthrust_weight_kg, hipthrust_reps, hipthrust_rpe,
                      squat_weight_kg, squat_reps, squat_rpe,
                      hipthrust_topset, squat_topset, notes
                    FROM workout_log
                    ORDER BY log_date ASC;
                    """
                ).fetchall()
                for row in legacy_rows:
                    now_iso = datetime.now().replace(microsecond=0).isoformat()
                    cur = conn.execute(
                        """
                        INSERT INTO workout_session (
                          log_date, session_order, session_done_yn, session_type,
                          class_done, rpe_session, notes, created_at, updated_at
                        )
                        VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            row["log_date"],
                            row["session_done_yn"],
                            row["session_type"] or "clase",
                            row["class_done"],
                            row["rpe_session"],
                            row["notes"],
                            now_iso,
                            now_iso,
                        ),
                    )
                    session_id = cur.lastrowid

                    legacy_exercises = []
                    ht_top = row["hipthrust_topset"] or _legacy_topset(
                        row["hipthrust_weight_kg"],
                        row["hipthrust_reps"],
                        row["hipthrust_rpe"],
                    )
                    if (
                        row["hipthrust_weight_kg"] is not None
                        or row["hipthrust_reps"] is not None
                        or row["hipthrust_rpe"] is not None
                        or ht_top
                    ):
                        legacy_exercises.append(
                            (
                                "Hip Thrust",
                                row["hipthrust_weight_kg"],
                                row["hipthrust_reps"],
                                row["hipthrust_rpe"],
                                ht_top,
                            )
                        )

                    sq_top = row["squat_topset"] or _legacy_topset(
                        row["squat_weight_kg"],
                        row["squat_reps"],
                        row["squat_rpe"],
                    )
                    if (
                        row["squat_weight_kg"] is not None
                        or row["squat_reps"] is not None
                        or row["squat_rpe"] is not None
                        or sq_top
                    ):
                        legacy_exercises.append(
                            (
                                "Sentadilla",
                                row["squat_weight_kg"],
                                row["squat_reps"],
                                row["squat_rpe"],
                                sq_top,
                            )
                        )

                    for idx, ex in enumerate(legacy_exercises, start=1):
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
                                idx,
                                ex[1],
                                ex[2],
                                ex[3],
                                ex[4],
                            ),
                        )
        except Exception:
            # No romper arranque por migracion legacy fallida.
            pass

        conn.commit()


ensure_schema()


@APP.errorhandler(RequestEntityTooLarge)
def handle_payload_too_large(_e):
    max_mb = int(APP.config.get("MAX_CONTENT_LENGTH", 0) / (1024 * 1024))
    return (
        jsonify(
            {
                "ok": False,
                "error": f"Archivo demasiado grande. Máximo permitido: {max_mb} MB.",
            }
        ),
        413,
    )


def valid_iso_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False


def safe_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None


def safe_int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except Exception:
        return None


def parse_summary_days(v, default: int = 7) -> int:
    n = safe_int(v)
    if n in SUMMARY_WINDOW_CHOICES:
        return int(n)
    if default in SUMMARY_WINDOW_CHOICES:
        return int(default)
    return 7


def parse_plan_adherence_days(v, default: int = 15) -> int:
    n = safe_int(v)
    if n in PLAN_ADHERENCE_WINDOW_CHOICES:
        return int(n)
    if default in PLAN_ADHERENCE_WINDOW_CHOICES:
        return int(default)
    return 15


def yn_or_none(v):
    if v is None:
        return None
    s = str(v).strip().upper()
    if s in ("Y", "N"):
        return s
    return None


def truthy(v) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "y", "yes", "on")


def yes_no(v, default="Y") -> str:
    if isinstance(v, bool):
        return "Y" if v else "N"
    s = str(v or "").strip().lower()
    if s in ("1", "true", "y", "yes", "on"):
        return "Y"
    if s in ("0", "false", "n", "no", "off"):
        return "N"
    return "Y" if str(default).strip().upper() != "N" else "N"


def today_iso() -> str:
    return datetime.now().date().isoformat()


def normalize_window_days(limit, default: int = 15, minimum: int = 1, maximum: int = 180) -> int:
    days = safe_int(limit)
    if days is None:
        days = int(default)
    days = max(int(minimum), days)
    days = min(int(maximum), days)
    return int(days)


def resolve_calendar_window(conn, source: str, limit, fallback_to_today: bool = False):
    days = normalize_window_days(limit, default=15, minimum=1, maximum=180)
    source_key = str(source or "").strip().lower()
    today_date = datetime.now().date()
    if source_key == "diet":
        row = conn.execute("SELECT MAX(log_date) AS max_date FROM diet_log;").fetchone()
    elif source_key == "workout":
        row = conn.execute("SELECT MAX(log_date) AS max_date FROM workout_session;").fetchone()
    elif source_key == "supplements":
        row = conn.execute("SELECT MAX(log_date) AS max_date FROM supplement_daily_log;").fetchone()
    else:
        row = None

    anchor_date = None
    if row and row["max_date"] and valid_iso_date(str(row["max_date"])):
        max_date = datetime.strptime(str(row["max_date"]), "%Y-%m-%d").date()
        anchor_date = max(max_date, today_date)
    elif fallback_to_today:
        anchor_date = today_date

    if anchor_date is None:
        return days, "", ""

    start_date = anchor_date - timedelta(days=max(0, days - 1))
    return days, start_date.isoformat(), anchor_date.isoformat()


def normalize_supplement_name(v: str) -> str:
    text = re.sub(r"\s+", " ", str(v or "").strip())
    return text[:80]


def auth_enabled() -> bool:
    if APP.config.get("TESTING"):
        return False
    if not AUTH_ENABLED:
        return False
    return bool(AUTH_PASSWORD_HASH)


def is_authenticated() -> bool:
    return bool(session.get("auth_ok"))


def safe_next_path(raw_next: str) -> str:
    nxt = str(raw_next or "").strip()
    if not nxt:
        return "/"
    if nxt.startswith("http://") or nxt.startswith("https://") or nxt.startswith("//"):
        return "/"
    if not nxt.startswith("/"):
        return "/"
    if nxt.startswith("/login"):
        return "/"
    return nxt


def unauthorized_response():
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "No autenticado"}), 401
    if request.path.startswith("/export/"):
        return jsonify({"ok": False, "error": "No autenticado"}), 401
    if request.path.startswith("/backup/"):
        return jsonify({"ok": False, "error": "No autenticado"}), 401
    if request.path.startswith("/uploads/") or request.path.startswith("/static/uploads/"):
        return jsonify({"ok": False, "error": "No autenticado"}), 401
    nxt = request.full_path.rstrip("?") if request.query_string else request.path
    return redirect(url_for("login_page", next=nxt))


def entry_mode(v) -> str:
    s = str(v or "").strip().lower()
    if s in ("create", "edit", "upsert"):
        return s
    return "upsert"


def normalize_session_type(v: str) -> str:
    s = str(v or "").strip().lower()
    if s == "mixta":
        # Compatibilidad legacy: "mixta" se interpreta como sesión de pesas.
        return "pesas"
    if s in ("clase", "pesas"):
        return s
    return "clase"


def normalize_exercise_name(v: str) -> str:
    text = re.sub(r"\s+", " ", str(v or "").strip())
    return text[:80]


def build_topset_text(weight, reps, rpe):
    if weight is None and reps is None and rpe is None:
        return None
    parts = []
    if weight is not None:
        parts.append(f"{weight:g}kg")
    if reps is not None:
        parts.append(f"{reps} reps")
    if rpe is not None:
        parts.append(f"RPE {rpe:g}")
    return " · ".join(parts) if parts else None


def parse_exercises_payload(data: dict):
    parsed = []

    def _append_exercise(payload: dict, allow_name_only: bool = True):
        name = normalize_exercise_name(payload.get("exercise_name") or payload.get("name"))
        weight = safe_float(payload.get("weight_kg"))
        reps = safe_int(payload.get("reps"))
        rpe = safe_float(payload.get("rpe"))
        topset_text = (payload.get("topset_text") or payload.get("topset") or "").strip()
        if not topset_text:
            topset_text = build_topset_text(weight, reps, rpe)
        has_metrics = weight is not None or reps is not None or rpe is not None or bool(topset_text)
        if not name and not has_metrics:
            return
        if not allow_name_only and not has_metrics:
            return
        if not name:
            name = f"Ejercicio {len(parsed) + 1}"
        parsed.append(
            {
                "exercise_name": name,
                "weight_kg": weight,
                "reps": reps,
                "rpe": rpe,
                "topset_text": topset_text,
            }
        )

    raw_exercises = data.get("exercises")
    if isinstance(raw_exercises, list):
        for item in raw_exercises:
            if isinstance(item, dict):
                _append_exercise(item, allow_name_only=True)

    raw_json = data.get("exercises_json")
    if raw_json and not parsed:
        try:
            decoded = json.loads(raw_json)
            if isinstance(decoded, list):
                for item in decoded:
                    if isinstance(item, dict):
                        _append_exercise(item, allow_name_only=True)
        except Exception:
            pass

    if not parsed:
        legacy = [
            {
                "exercise_name": "Hip Thrust",
                "weight_kg": data.get("hipthrust_weight_kg"),
                "reps": data.get("hipthrust_reps"),
                "rpe": data.get("hipthrust_rpe"),
                "topset_text": data.get("hipthrust_topset"),
            },
            {
                "exercise_name": "Sentadilla",
                "weight_kg": data.get("squat_weight_kg"),
                "reps": data.get("squat_reps"),
                "rpe": data.get("squat_rpe"),
                "topset_text": data.get("squat_topset"),
            },
        ]
        for item in legacy:
            _append_exercise(item, allow_name_only=False)

    return parsed[:24]


DIET_IMPORT_FIELDS = (
    "log_date",
    "sleep_hours",
    "sleep_quality",
    "steps",
    "weight_kg",
    "waist_cm",
    "hip_cm",
    "alcohol_units",
    "creatine_yn",
    "photo_yn",
    "photo_path",
)

DIET_IMPORT_HEADER_ALIASES = {
    "log_date": "log_date",
    "date": "log_date",
    "fecha": "log_date",
    "sleep_hours": "sleep_hours",
    "sleep": "sleep_hours",
    "sueno_horas": "sleep_hours",
    "sueno": "sleep_hours",
    "sleep_quality": "sleep_quality",
    "quality": "sleep_quality",
    "calidad_sueno": "sleep_quality",
    "calidad": "sleep_quality",
    "steps": "steps",
    "pasos": "steps",
    "weight_kg": "weight_kg",
    "peso_kg": "weight_kg",
    "peso": "weight_kg",
    "waist_cm": "waist_cm",
    "cintura_cm": "waist_cm",
    "cintura": "waist_cm",
    "hip_cm": "hip_cm",
    "cadera_cm": "hip_cm",
    "cadera": "hip_cm",
    "alcohol_units": "alcohol_units",
    "alcohol": "alcohol_units",
    "creatine_yn": "creatine_yn",
    "creatina_yn": "creatine_yn",
    "creatina": "creatine_yn",
    "photo_yn": "photo_yn",
    "foto_yn": "photo_yn",
    "foto": "photo_yn",
    "photo_path": "photo_path",
    "foto_path": "photo_path",
}

PLAN_DIET_FIELDS = (
    "log_date",
    "calories_target_kcal",
    "protein_target_g",
    "carbs_target_g",
    "fat_target_g",
    "breakfast",
    "snack_1",
    "lunch",
    "snack_2",
    "dinner",
    "notes",
)

PLAN_DIET_REQUIRED = (
    "log_date",
    "calories_target_kcal",
    "protein_target_g",
    "carbs_target_g",
    "fat_target_g",
    "breakfast",
    "snack_1",
    "lunch",
    "snack_2",
    "dinner",
)

PLAN_DIET_HEADER_ALIASES = {
    "date": "log_date",
    "log_date": "log_date",
    "fecha": "log_date",
    "calories_target_kcal": "calories_target_kcal",
    "kcal_target": "calories_target_kcal",
    "protein_target_g": "protein_target_g",
    "carbs_target_g": "carbs_target_g",
    "fat_target_g": "fat_target_g",
    "breakfast": "breakfast",
    "snack_1": "snack_1",
    "snack1": "snack_1",
    "lunch": "lunch",
    "snack_2": "snack_2",
    "snack2": "snack_2",
    "dinner": "dinner",
    "notes": "notes",
}

PLAN_WORKOUT_SESSION_FIELDS = (
    "log_date",
    "plan_session_id",
    "session_type",
    "warmup",
    "class_sessions",
    "cardio",
    "mobility_cooldown",
    "additional_exercises",
    "notes",
)

PLAN_WORKOUT_SESSION_REQUIRED = (
    "log_date",
    "plan_session_id",
    "session_type",
)

PLAN_WORKOUT_SESSION_HEADER_ALIASES = {
    "date": "log_date",
    "log_date": "log_date",
    "fecha": "log_date",
    "session_id": "plan_session_id",
    "plan_session_id": "plan_session_id",
    "session_type": "session_type",
    "tipo_sesion": "session_type",
    "warmup": "warmup",
    "class_sessions": "class_sessions",
    "sessions_class": "class_sessions",
    "cardio": "cardio",
    "mobility_cooldown": "mobility_cooldown",
    "additional_exercises": "additional_exercises",
    "notes": "notes",
}

PLAN_WORKOUT_EXERCISE_FIELDS = (
    "log_date",
    "plan_session_id",
    "exercise_order",
    "exercise_name",
    "target_sets",
    "target_reps_min",
    "target_reps_max",
    "target_weight_kg",
    "target_rpe",
    "intensity_target",
    "progression_weight_rule",
    "progression_reps_rule",
)

PLAN_WORKOUT_EXERCISE_REQUIRED = (
    "log_date",
    "plan_session_id",
    "exercise_order",
    "exercise_name",
)

PLAN_WORKOUT_EXERCISE_HEADER_ALIASES = {
    "date": "log_date",
    "log_date": "log_date",
    "fecha": "log_date",
    "session_id": "plan_session_id",
    "plan_session_id": "plan_session_id",
    "exercise_order": "exercise_order",
    "order": "exercise_order",
    "exercise_name": "exercise_name",
    "name": "exercise_name",
    "target_sets": "target_sets",
    "target_reps_min": "target_reps_min",
    "target_reps_max": "target_reps_max",
    "target_weight_kg": "target_weight_kg",
    "target_rpe": "target_rpe",
    "intensity_target": "intensity_target",
    "progression_weight_rule": "progression_weight_rule",
    "progression_reps_rule": "progression_reps_rule",
}

PLAN_WORKOUT_COMBINED_BASE_FIELDS = (
    "log_date",
    "session_type",
    "warmup",
    "class_sessions",
    "cardio",
    "mobility_cooldown",
    "additional_exercises",
    "notes",
)

PLAN_WORKOUT_COMBINED_EXERCISE_SLOTS = 6
PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIXES = (
    "name",
    "sets",
    "reps_min",
    "reps_max",
    "weight_kg",
    "rpe",
    "intensity_target",
    "progression_weight_rule",
    "progression_reps_rule",
)

PLAN_WORKOUT_COMBINED_FIELDS = PLAN_WORKOUT_COMBINED_BASE_FIELDS + tuple(
    f"exercise_{slot}_{suffix}"
    for slot in range(1, PLAN_WORKOUT_COMBINED_EXERCISE_SLOTS + 1)
    for suffix in PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIXES
)

PLAN_WORKOUT_COMBINED_REQUIRED = (
    "log_date",
    "session_type",
)

PLAN_WORKOUT_COMBINED_HEADER_ALIASES = {
    "date": "log_date",
    "log_date": "log_date",
    "fecha": "log_date",
    "session_type": "session_type",
    "tipo_sesion": "session_type",
    "warmup": "warmup",
    "class_sessions": "class_sessions",
    "sessions_class": "class_sessions",
    "cardio": "cardio",
    "mobility_cooldown": "mobility_cooldown",
    "additional_exercises": "additional_exercises",
    "notes": "notes",
}

PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIX_ALIASES = {
    "name": "name",
    "exercise_name": "name",
    "sets": "sets",
    "target_sets": "sets",
    "reps_min": "reps_min",
    "target_reps_min": "reps_min",
    "reps_max": "reps_max",
    "target_reps_max": "reps_max",
    "weight_kg": "weight_kg",
    "target_weight_kg": "weight_kg",
    "weight": "weight_kg",
    "rpe": "rpe",
    "target_rpe": "rpe",
    "intensity_target": "intensity_target",
    "intensity": "intensity_target",
    "progression_weight_rule": "progression_weight_rule",
    "progression_weight": "progression_weight_rule",
    "progression_reps_rule": "progression_reps_rule",
    "progression_reps": "progression_reps_rule",
}

PLAN_SCORE_ALLOWED = (0.0, 0.5, 1.0)


def normalize_header_name(name: str) -> str:
    txt = unicodedata.normalize("NFKD", str(name or ""))
    txt = txt.encode("ascii", "ignore").decode("ascii")
    txt = txt.strip().lower()
    txt = re.sub(r"[\s\-/]+", "_", txt)
    txt = re.sub(r"[^a-z0-9_]+", "", txt)
    return txt


def canonical_diet_header(name: str) -> str:
    key = normalize_header_name(name)
    return DIET_IMPORT_HEADER_ALIASES.get(key, key)


def canonical_plan_diet_header(name: str) -> str:
    key = normalize_header_name(name)
    return PLAN_DIET_HEADER_ALIASES.get(key, key)


def canonical_plan_workout_session_header(name: str) -> str:
    key = normalize_header_name(name)
    return PLAN_WORKOUT_SESSION_HEADER_ALIASES.get(key, key)


def canonical_plan_workout_exercise_header(name: str) -> str:
    key = normalize_header_name(name)
    return PLAN_WORKOUT_EXERCISE_HEADER_ALIASES.get(key, key)


def canonical_plan_workout_combined_header(name: str) -> str:
    key = normalize_header_name(name)
    direct = PLAN_WORKOUT_COMBINED_HEADER_ALIASES.get(key)
    if direct:
        return direct

    m = re.match(r"^(?:exercise|ex)_?(\d+)_([a-z0-9_]+)$", key)
    if not m:
        m = re.match(r"^(?:exercise|ex)(\d+)_?([a-z0-9_]+)$", key)
    if not m:
        return key

    slot = safe_int(m.group(1))
    suffix_raw = m.group(2) or ""
    suffix = PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIX_ALIASES.get(suffix_raw, suffix_raw)
    if (
        slot is None
        or slot < 1
        or slot > PLAN_WORKOUT_COMBINED_EXERCISE_SLOTS
        or suffix not in PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIXES
    ):
        return key
    return f"exercise_{slot}_{suffix}"


def parse_plan_csv_rows(
    text: str,
    *,
    canonical_header_fn,
    required_fields,
):
    reader = _build_csv_reader(text)
    headers_raw = next(reader, None)
    if not headers_raw:
        raise ValueError("CSV vacio o sin encabezados.")

    headers = [canonical_header_fn(h) for h in headers_raw]
    if len(headers) != len(set(headers)):
        raise ValueError("Hay columnas repetidas en el CSV (tras normalizar encabezados).")

    missing = [f for f in required_fields if f not in headers]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")

    rows = []
    for line_no, row in enumerate(reader, start=2):
        trimmed_cells = [str(cell or "").strip() for cell in row]
        non_empty_cells = [cell for cell in trimmed_cells if cell]
        if not non_empty_cells:
            continue
        # Permite plantillas guiadas con filas de ayuda tipo #TYPE_HINT / #RULE_HINT.
        if non_empty_cells[0].startswith("#"):
            continue
        mapped = {}
        for idx, key in enumerate(headers):
            if not key:
                continue
            mapped[key] = row[idx].strip() if idx < len(row) else ""
        rows.append((line_no, mapped))
    return rows


def _clip_text(v, max_len: int):
    txt = re.sub(r"\s+", " ", str(v or "").strip())
    return txt[:max_len]


def parse_plan_diet_row(raw_row: dict):
    row = raw_row or {}
    out = {k: None for k in PLAN_DIET_FIELDS}
    errors = []

    log_date = str(row.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        errors.append("date invalida (formato AAAA-MM-DD)")
    out["log_date"] = log_date

    for field, max_v in (
        ("calories_target_kcal", 12000),
        ("protein_target_g", 800),
        ("carbs_target_g", 1500),
        ("fat_target_g", 500),
    ):
        val, err = parse_csv_float(row.get(field))
        if err or val is None:
            errors.append(f"{field} invalido")
            continue
        if val < 0 or val > max_v:
            errors.append(f"{field} fuera de rango")
            continue
        out[field] = float(val)

    out["breakfast"] = _clip_text(row.get("breakfast"), 600)
    out["snack_1"] = _clip_text(row.get("snack_1"), 600)
    out["lunch"] = _clip_text(row.get("lunch"), 600)
    out["snack_2"] = _clip_text(row.get("snack_2"), 600)
    out["dinner"] = _clip_text(row.get("dinner"), 600)
    out["notes"] = _clip_text(row.get("notes"), 600)

    for meal_field in ("breakfast", "snack_1", "lunch", "snack_2", "dinner"):
        if not out[meal_field]:
            errors.append(f"{meal_field} no puede estar vacio")

    return out, errors


def parse_plan_workout_session_row(raw_row: dict):
    row = raw_row or {}
    out = {k: None for k in PLAN_WORKOUT_SESSION_FIELDS}
    errors = []

    log_date = str(row.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        errors.append("date invalida (formato AAAA-MM-DD)")
    out["log_date"] = log_date

    plan_session_id = _clip_text(row.get("plan_session_id"), 48)
    if not plan_session_id:
        errors.append("session_id obligatorio")
    out["plan_session_id"] = plan_session_id

    raw_type = str(row.get("session_type") or "").strip().lower()
    if raw_type == "mixta":
        errors.append("session_type 'mixta' ya no existe: usa 'clase' o 'pesas'")
    elif raw_type not in ("clase", "pesas"):
        errors.append("session_type debe ser clase o pesas")
    out["session_type"] = raw_type if raw_type in ("clase", "pesas") else "clase"

    out["warmup"] = _clip_text(row.get("warmup"), 700)
    out["class_sessions"] = _clip_text(row.get("class_sessions"), 700)
    out["cardio"] = _clip_text(row.get("cardio"), 700)
    out["mobility_cooldown"] = _clip_text(row.get("mobility_cooldown"), 700)
    out["additional_exercises"] = _clip_text(row.get("additional_exercises"), 700)
    out["notes"] = _clip_text(row.get("notes"), 700)

    return out, errors


def parse_plan_workout_exercise_row(raw_row: dict):
    row = raw_row or {}
    out = {k: None for k in PLAN_WORKOUT_EXERCISE_FIELDS}
    errors = []

    log_date = str(row.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        errors.append("date invalida (formato AAAA-MM-DD)")
    out["log_date"] = log_date

    plan_session_id = _clip_text(row.get("plan_session_id"), 48)
    if not plan_session_id:
        errors.append("session_id obligatorio")
    out["plan_session_id"] = plan_session_id

    exercise_order, err = parse_csv_int(row.get("exercise_order"))
    if err or exercise_order is None:
        errors.append("exercise_order invalido")
    elif exercise_order < 1 or exercise_order > 32:
        errors.append("exercise_order fuera de rango (1-32)")
    out["exercise_order"] = exercise_order

    ex_name = _clip_text(row.get("exercise_name"), 90)
    if not ex_name:
        errors.append("exercise_name obligatorio")
    out["exercise_name"] = ex_name

    target_sets, err = parse_csv_int(row.get("target_sets"))
    if err:
        errors.append("target_sets invalido")
    elif target_sets is not None and (target_sets < 1 or target_sets > 12):
        errors.append("target_sets fuera de rango (1-12)")
    out["target_sets"] = target_sets

    target_reps_min, err = parse_csv_int(row.get("target_reps_min"))
    if err:
        errors.append("target_reps_min invalido")
    elif target_reps_min is not None and (target_reps_min < 1 or target_reps_min > 100):
        errors.append("target_reps_min fuera de rango (1-100)")
    out["target_reps_min"] = target_reps_min

    target_reps_max, err = parse_csv_int(row.get("target_reps_max"))
    if err:
        errors.append("target_reps_max invalido")
    elif target_reps_max is not None and (target_reps_max < 1 or target_reps_max > 100):
        errors.append("target_reps_max fuera de rango (1-100)")
    out["target_reps_max"] = target_reps_max

    if (
        target_reps_min is not None
        and target_reps_max is not None
        and target_reps_min > target_reps_max
    ):
        errors.append("target_reps_min no puede ser mayor que target_reps_max")

    target_weight_kg, err = parse_csv_float(row.get("target_weight_kg"))
    if err:
        errors.append("target_weight_kg invalido")
    elif target_weight_kg is not None and (target_weight_kg < 0 or target_weight_kg > 1000):
        errors.append("target_weight_kg fuera de rango")
    out["target_weight_kg"] = target_weight_kg

    target_rpe, err = parse_csv_float(row.get("target_rpe"))
    if err:
        errors.append("target_rpe invalido")
    elif target_rpe is not None and (target_rpe < 1 or target_rpe > 10):
        errors.append("target_rpe fuera de rango (1-10)")
    out["target_rpe"] = target_rpe

    out["intensity_target"] = _clip_text(row.get("intensity_target"), 140)
    out["progression_weight_rule"] = _clip_text(row.get("progression_weight_rule"), 240)
    out["progression_reps_rule"] = _clip_text(row.get("progression_reps_rule"), 240)

    return out, errors


def parse_plan_workout_combined_row(raw_row: dict):
    row = raw_row or {}
    out = {k: None for k in PLAN_WORKOUT_COMBINED_BASE_FIELDS}
    out["exercises"] = []
    errors = []
    warnings = []

    log_date = str(row.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        errors.append("date invalida (formato AAAA-MM-DD)")
    out["log_date"] = log_date

    raw_type = str(row.get("session_type") or "").strip().lower()
    if raw_type == "mixta":
        errors.append("session_type 'mixta' ya no existe: usa 'clase' o 'pesas'")
    elif raw_type not in ("clase", "pesas"):
        errors.append("session_type debe ser clase o pesas")
    out["session_type"] = raw_type if raw_type in ("clase", "pesas") else "clase"

    out["warmup"] = _clip_text(row.get("warmup"), 700)
    out["class_sessions"] = _clip_text(row.get("class_sessions"), 700)
    out["cardio"] = _clip_text(row.get("cardio"), 700)
    out["mobility_cooldown"] = _clip_text(row.get("mobility_cooldown"), 700)
    out["additional_exercises"] = _clip_text(row.get("additional_exercises"), 700)
    out["notes"] = _clip_text(row.get("notes"), 700)

    for slot in range(1, PLAN_WORKOUT_COMBINED_EXERCISE_SLOTS + 1):
        prefix = f"exercise_{slot}_"
        raw_slot = {
            suffix: row.get(f"{prefix}{suffix}")
            for suffix in PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIXES
        }
        if not any(str(v or "").strip() for v in raw_slot.values()):
            continue

        slot_errors = []
        item = {
            "exercise_order": slot,
            "exercise_name": "",
            "target_sets": None,
            "target_reps_min": None,
            "target_reps_max": None,
            "target_weight_kg": None,
            "target_rpe": None,
            "intensity_target": "",
            "progression_weight_rule": "",
            "progression_reps_rule": "",
        }

        ex_name = _clip_text(raw_slot.get("name"), 90)
        if not ex_name:
            slot_errors.append("name obligatorio")
        item["exercise_name"] = ex_name

        target_sets, err = parse_csv_int(raw_slot.get("sets"))
        if err:
            slot_errors.append("sets invalido")
        elif target_sets is not None and (target_sets < 1 or target_sets > 12):
            slot_errors.append("sets fuera de rango (1-12)")
        item["target_sets"] = target_sets

        target_reps_min, err = parse_csv_int(raw_slot.get("reps_min"))
        if err:
            slot_errors.append("reps_min invalido")
        elif target_reps_min is not None and (target_reps_min < 1 or target_reps_min > 100):
            slot_errors.append("reps_min fuera de rango (1-100)")
        item["target_reps_min"] = target_reps_min

        target_reps_max, err = parse_csv_int(raw_slot.get("reps_max"))
        if err:
            slot_errors.append("reps_max invalido")
        elif target_reps_max is not None and (target_reps_max < 1 or target_reps_max > 100):
            slot_errors.append("reps_max fuera de rango (1-100)")
        item["target_reps_max"] = target_reps_max

        if (
            target_reps_min is not None
            and target_reps_max is not None
            and target_reps_min > target_reps_max
        ):
            slot_errors.append("reps_min no puede ser mayor que reps_max")

        target_weight_kg, err = parse_csv_float(raw_slot.get("weight_kg"))
        if err:
            slot_errors.append("weight_kg invalido")
        elif target_weight_kg is not None and (target_weight_kg < 0 or target_weight_kg > 1000):
            slot_errors.append("weight_kg fuera de rango")
        item["target_weight_kg"] = target_weight_kg

        target_rpe, err = parse_csv_float(raw_slot.get("rpe"))
        if err:
            slot_errors.append("rpe invalido")
        elif target_rpe is not None and (target_rpe < 1 or target_rpe > 10):
            slot_errors.append("rpe fuera de rango (1-10)")
        item["target_rpe"] = target_rpe

        item["intensity_target"] = _clip_text(raw_slot.get("intensity_target"), 140)
        item["progression_weight_rule"] = _clip_text(raw_slot.get("progression_weight_rule"), 240)
        item["progression_reps_rule"] = _clip_text(raw_slot.get("progression_reps_rule"), 240)

        if slot_errors:
            errors.append(f"exercise_{slot}: {'; '.join(slot_errors)}")
            continue
        out["exercises"].append(item)

    if out["session_type"] == "clase" and out["exercises"]:
        warnings.append(
            f"session_type clase: se ignoraron {len(out['exercises'])} ejercicios (solo aplican a pesas)"
        )
        out["exercises"] = []

    return out, errors, warnings


def parse_plan_score(v):
    if v is None or v == "":
        return None
    try:
        val = float(v)
    except Exception:
        return None
    rounded = round(val, 2)
    if rounded in PLAN_SCORE_ALLOWED:
        return rounded
    return None


def parse_csv_float(v):
    raw = str(v or "").strip()
    if not raw:
        return None, None
    raw = raw.replace(",", ".")
    try:
        return float(raw), None
    except Exception:
        return None, "valor numerico invalido"


def parse_csv_int(v):
    raw = str(v or "").strip()
    if not raw:
        return None, None
    raw = raw.replace(",", ".")
    try:
        num = float(raw)
    except Exception:
        return None, "valor entero invalido"
    if not num.is_integer():
        return None, "debe ser entero"
    return int(num), None


def normalize_import_photo_path(path_value: str) -> str:
    rel = str(path_value or "").strip().replace("\\", "/")
    if not rel:
        return ""
    rel = rel.lstrip("/")
    if rel.startswith("static/uploads/"):
        rel = rel[len("static/") :]
    if not rel.startswith("uploads/"):
        return ""
    parts = [p for p in rel.split("/") if p]
    if any(p == ".." for p in parts):
        return ""
    return "/".join(parts)


def read_text_file_storage(file_storage) -> str:
    raw = file_storage.read() if file_storage else b""
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    raise ValueError("No se pudo leer el CSV (encoding no soportado).")


def _build_csv_reader(text: str):
    source = str(text or "")
    delimiter = ","
    for raw_line in source.splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        counts = {
            ",": line.count(","),
            ";": line.count(";"),
            "\t": line.count("\t"),
            "|": line.count("|"),
        }
        best, best_count = max(counts.items(), key=lambda item: item[1])
        if best_count > 0:
            delimiter = best
        break
    return csv.reader(StringIO(source, newline=""), delimiter=delimiter)


def parse_diet_import_csv(text: str):
    reader = _build_csv_reader(text)
    headers_raw = next(reader, None)
    if not headers_raw:
        raise ValueError("CSV vacio o sin encabezados.")

    headers = [canonical_diet_header(h) for h in headers_raw]
    if "log_date" not in headers:
        raise ValueError("Falta columna obligatoria: log_date (o fecha).")
    if len(headers) != len(set(headers)):
        raise ValueError("Hay columnas repetidas en el CSV (tras normalizar encabezados).")

    rows = []
    for line_no, row in enumerate(reader, start=2):
        if not any(str(cell or "").strip() for cell in row):
            continue
        mapped = {}
        for idx, key in enumerate(headers):
            if not key:
                continue
            mapped[key] = row[idx].strip() if idx < len(row) else ""
        rows.append((line_no, mapped))
    return rows


def parse_diet_import_row(raw_row: dict):
    row = raw_row or {}
    out = {k: None for k in DIET_IMPORT_FIELDS}
    errors = []
    warnings = []

    log_date = str(row.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        errors.append("log_date invalida (formato AAAA-MM-DD)")
    out["log_date"] = log_date

    sleep_hours, err = parse_csv_float(row.get("sleep_hours"))
    if err:
        errors.append(f"sleep_hours {err}")
    out["sleep_hours"] = sleep_hours

    sleep_quality, err = parse_csv_int(row.get("sleep_quality"))
    if err:
        errors.append(f"sleep_quality {err}")
    elif sleep_quality is not None and (sleep_quality < 1 or sleep_quality > 10):
        errors.append("sleep_quality fuera de rango (1-10)")
    out["sleep_quality"] = sleep_quality

    steps, err = parse_csv_int(row.get("steps"))
    if err:
        errors.append(f"steps {err}")
    elif steps is not None and steps < 0:
        errors.append("steps no puede ser negativo")
    out["steps"] = steps

    weight_kg, err = parse_csv_float(row.get("weight_kg"))
    if err:
        errors.append(f"weight_kg {err}")
    out["weight_kg"] = weight_kg

    waist_cm, err = parse_csv_float(row.get("waist_cm"))
    if err:
        errors.append(f"waist_cm {err}")
    out["waist_cm"] = waist_cm

    hip_cm, err = parse_csv_float(row.get("hip_cm"))
    if err:
        errors.append(f"hip_cm {err}")
    out["hip_cm"] = hip_cm

    alcohol_units, err = parse_csv_int(row.get("alcohol_units"))
    if err:
        errors.append(f"alcohol_units {err}")
    alcohol_units = 0 if alcohol_units is None else alcohol_units
    if alcohol_units < 0:
        errors.append("alcohol_units no puede ser negativo")
    out["alcohol_units"] = alcohol_units

    creatine_raw = str(row.get("creatine_yn") or "").strip()
    creatine_yn = yn_or_none(creatine_raw)
    if creatine_raw and creatine_yn is None:
        errors.append("creatine_yn debe ser Y o N")
    out["creatine_yn"] = creatine_yn

    photo_flag_raw = str(row.get("photo_yn") or "").strip()
    photo_yn = yn_or_none(photo_flag_raw)
    if photo_flag_raw and photo_yn is None:
        errors.append("photo_yn debe ser Y o N")

    photo_path_raw = str(row.get("photo_path") or "").strip()
    photo_path = normalize_import_photo_path(photo_path_raw)
    if photo_path_raw and not photo_path:
        warnings.append("photo_path ignorado (ruta no valida)")

    if photo_path:
        out["photo_yn"] = "Y"
        out["photo_path"] = photo_path
    else:
        if photo_yn == "Y":
            warnings.append("photo_yn=Y sin photo_path valido: se omite marca de foto")
            out["photo_yn"] = None
        else:
            out["photo_yn"] = photo_yn
        out["photo_path"] = ""

    return out, errors, warnings


def classify_diet_import_rows(rows, existing_dates):
    preview = []
    seen_dates = set()
    counts = {"total": 0, "valid": 0, "conflict": 0, "invalid": 0}

    for line_no, mapped in rows:
        counts["total"] += 1
        normalized, errors, warnings = parse_diet_import_row(mapped)
        date = normalized.get("log_date") or ""

        status = "valid"
        reasons = []

        if errors:
            status = "invalid"
            reasons.extend(errors)
        elif not date:
            status = "invalid"
            reasons.append("log_date faltante")
        elif date in seen_dates:
            status = "invalid"
            reasons.append("fecha duplicada dentro del CSV")
        elif date in existing_dates:
            status = "conflict"
            reasons.append("la fecha ya existe en la base local")

        if date:
            seen_dates.add(date)
        if warnings:
            reasons.extend(warnings)

        counts[status] += 1
        preview.append(
            {
                "row_number": line_no,
                "status": status,
                "reason": "; ".join(reasons),
                "row": normalized,
            }
        )

    return {"summary": counts, "preview": preview}


# -----------------------------
# Photos
# -----------------------------
def photo_url_from_rel(rel_path: str) -> str:
    rel_path = (rel_path or "").lstrip("/")
    if not rel_path:
        return ""
    # Normaliza rutas legacy "static/uploads/..." y actuales "uploads/..."
    # para servirlas por el endpoint explícito /uploads/...
    rel_path = rel_path.replace("\\", "/")
    if rel_path.startswith("static/uploads/"):
        rel_path = rel_path[len("static/") :]
    if rel_path.startswith("uploads/"):
        return "/" + rel_path
    return "/" + rel_path


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "")
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base).strip("_")
    if not base:
        base = "photo"
    return base


def ensure_upload_dir(log_date: str) -> str:
    date_dir = os.path.join(UPLOAD_ROOT, log_date)
    os.makedirs(date_dir, exist_ok=True)
    return date_dir


def _read_upload_bytes(file_storage) -> bytes:
    stream = getattr(file_storage, "stream", None)
    if stream is None:
        return b""
    pos = None
    try:
        pos = stream.tell()
    except Exception:
        pos = None
    try:
        if pos is not None:
            stream.seek(0)
        return stream.read() or b""
    finally:
        try:
            if pos is not None:
                stream.seek(pos)
            else:
                stream.seek(0)
        except Exception:
            pass


def _compress_photo_bytes(raw_bytes: bytes, original_ext: str):
    """
    Devuelve `(bytes_comprimidos, extension_destino)` o `None` si no se puede
    comprimir (falta Pillow, archivo no decodificable o no mejora el tamaño).
    """
    if not raw_bytes or not PHOTO_COMPRESSION_ENABLED or not PILLOW_AVAILABLE:
        return None

    try:
        with Image.open(BytesIO(raw_bytes)) as img:
            img.load()
            img = ImageOps.exif_transpose(img)
            if max(img.width, img.height) > PHOTO_MAX_SIDE:
                resampling = getattr(Image, "Resampling", None)
                lanczos = (
                    resampling.LANCZOS
                    if resampling is not None
                    else getattr(Image, "LANCZOS", None)
                )
                if lanczos is not None:
                    img.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE), resample=lanczos)
                else:
                    img.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE))

            target_ext = original_ext.lower()
            save_format = ""
            save_kwargs = {}

            if PHOTO_PREFER_WEBP:
                target_ext = ".webp"
                save_format = "WEBP"
                save_kwargs = {"quality": PHOTO_QUALITY, "method": 6}
            elif target_ext in (".jpg", ".jpeg"):
                target_ext = ".jpg"
                save_format = "JPEG"
                save_kwargs = {"quality": PHOTO_QUALITY, "optimize": True, "progressive": True}
            elif target_ext == ".png":
                save_format = "PNG"
                save_kwargs = {"optimize": True, "compress_level": 8}
            elif target_ext == ".webp":
                save_format = "WEBP"
                save_kwargs = {"quality": PHOTO_QUALITY, "method": 6}
            else:
                return None

            if save_format == "JPEG" and img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            out = BytesIO()
            img.save(out, format=save_format, **save_kwargs)
            candidate = out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    except Exception:
        return None

    if not candidate:
        return None
    if len(candidate) >= len(raw_bytes):
        return None
    return candidate, target_ext


def save_progress_photo(file_storage, log_date: str) -> str:
    # Valida fecha
    if not valid_iso_date(log_date):
        raise ValueError("log_date inválida")

    # Valida extensión
    original = getattr(file_storage, "filename", "") or ""
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Extensión de archivo no permitida")

    date_dir = ensure_upload_dir(log_date)
    raw_bytes = _read_upload_bytes(file_storage)
    final_ext = ext
    payload_bytes = raw_bytes if raw_bytes else None
    compressed = _compress_photo_bytes(raw_bytes, ext)
    if compressed:
        payload_bytes, final_ext = compressed

    stamp = datetime.now().strftime("%H%M%S%f")
    safe_name = sanitize_filename(os.path.splitext(original)[0])
    filename = f"{safe_name}_{stamp}{final_ext}"

    abs_path = os.path.join(date_dir, filename)
    if payload_bytes is None:
        file_storage.save(abs_path)
    else:
        with open(abs_path, "wb") as fh:
            fh.write(payload_bytes)

    # Guardamos en DB una ruta relativa estable (independiente de static folder).
    rel = os.path.join("uploads", log_date, filename).replace("\\", "/")
    return rel


def get_existing_photo_rel(conn, log_date: str, kind: str) -> str:
    row = conn.execute(
        "SELECT path FROM photo_log WHERE log_date = ? AND kind = ?;",
        (log_date, kind),
    ).fetchone()
    return (row["path"] if row else "") or ""


def photo_rel_to_abs(rel_path: str) -> str:
    rel_path = (rel_path or "").lstrip("/").replace("\\", "/")
    if rel_path.startswith("static/uploads/"):
        suffix = rel_path[len("static/uploads/") :]
    elif rel_path.startswith("uploads/"):
        suffix = rel_path[len("uploads/") :]
    else:
        return ""
    return os.path.normpath(os.path.join(UPLOAD_ROOT, suffix))


def safe_delete_uploaded_photo(rel_path: str) -> bool:
    """
    Borra un archivo solo si está dentro de static/uploads/.
    Además intenta limpiar directorios vacíos hasta static/uploads.
    """
    if not rel_path:
        return False

    rel_path = rel_path.lstrip("/").replace("\\", "/")

    # Aceptamos rutas legacy uploads/... y actuales static/uploads/...
    if not (rel_path.startswith("static/uploads/") or rel_path.startswith("uploads/")):
        return False

    abs_candidate = photo_rel_to_abs(rel_path)
    if not abs_candidate:
        return False

    # Verifica que sigue dentro de static/uploads
    abs_root = os.path.normpath(UPLOAD_ROOT)
    if os.path.commonpath([abs_candidate, abs_root]) != abs_root:
        return False

    # Si no existe, lo consideramos OK (evita fallos si el usuario borró manualmente)
    if not os.path.exists(abs_candidate):
        return True
    if not os.path.isfile(abs_candidate):
        return False

    try:
        os.remove(abs_candidate)
    except Exception:
        return False

    # Limpieza de carpetas vacías (log_date)
    try:
        d = os.path.dirname(abs_candidate)
        while d and os.path.normpath(d).startswith(abs_root):
            if os.listdir(d):
                break
            os.rmdir(d)
            d = os.path.dirname(d)
    except Exception:
        # No es crítico si falla la limpieza
        pass

    return True


# -----------------------------
# Reads
# -----------------------------
def _avg(values):
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _row_whr(row) -> float:
    try:
        waist = float(row["waist_cm"])
        hip = float(row["hip_cm"])
    except Exception:
        return None
    if hip <= 0:
        return None
    return waist / hip


def _first_last(items):
    if not items:
        return None, None
    return items[0], items[-1]


def _summary_series(rows):
    points = []
    for r in rows:
        points.append(
            {
                "log_date": r["log_date"],
                "sleep_hours": r["sleep_hours"],
                "steps": r["steps"],
                "weight_kg": r["weight_kg"],
                "whr": _row_whr(r),
            }
        )
    return points


def _trend_message(weight_delta, whr_delta):
    if weight_delta is None or whr_delta is None:
        return (
            "Aun no hay datos suficientes para sacar una conclusion clara.",
            "muted",
        )

    wd = float(weight_delta)
    hd = float(whr_delta)
    weight_stable = abs(wd) <= 0.2
    whr_stable = abs(hd) <= 0.005

    if weight_stable and whr_stable:
        return ("Todo va estable: casi sin cambios en peso ni cintura/cadera.", "muted")
    if wd < 0 and hd < 0:
        return ("Buena señal: bajan el peso y la relacion cintura/cadera.", "good")
    if wd > 0 and hd < 0:
        return (
            "Buena señal: sube algo el peso, pero mejora la cintura/cadera.",
            "good",
        )
    if wd < 0 and hd > 0:
        return (
            "Señal mixta: bajas peso, pero la cintura/cadera empeora un poco.",
            "warn",
        )
    if wd > 0 and hd > 0:
        return (
            "Ojo: suben peso y cintura/cadera a la vez.",
            "warn",
        )
    if wd > 0 and whr_stable:
        return (
            "Sube el peso, con cintura/cadera bastante estable.",
            "muted",
        )
    if wd < 0 and whr_stable:
        return (
            "Baja el peso, con cintura/cadera bastante estable.",
            "muted",
        )
    if weight_stable and hd < 0:
        return ("Peso estable y cintura/cadera mejorando.", "good")
    if weight_stable and hd > 0:
        return ("Peso estable, pero cintura/cadera empeora: vigila la tendencia.", "warn")
    return ("Tendencia mixta: interpretala junto con entreno, dieta y descanso.", "muted")


def fetch_summary(conn, date_from: str = "", date_to: str = "", rolling_days: int = 7):
    rolling_days = parse_summary_days(rolling_days, default=7)
    use_range = (
        valid_iso_date(date_from)
        and valid_iso_date(date_to)
        and str(date_from) <= str(date_to)
    )

    window_from = ""
    window_to = ""
    coverage_target = 0

    if use_range:
        rows = conn.execute(
            """
            SELECT log_date, sleep_hours, steps, weight_kg, waist_cm, hip_cm
            FROM diet_log
            WHERE log_date BETWEEN ? AND ?
            ORDER BY log_date ASC;
            """,
            (date_from, date_to),
        ).fetchall()
        mode = "range"
        period_label = f"{date_from} -> {date_to}"
        window_from = date_from
        window_to = date_to
        coverage_target = (datetime.strptime(date_to, "%Y-%m-%d").date() - datetime.strptime(date_from, "%Y-%m-%d").date()).days + 1
    else:
        today = datetime.now().date()
        rolling_from = today - timedelta(days=max(0, rolling_days - 1))
        rolling_to = today
        rows = conn.execute(
            """
            SELECT log_date, sleep_hours, steps, weight_kg, waist_cm, hip_cm
            FROM diet_log
            WHERE log_date BETWEEN ? AND ?
            ORDER BY log_date ASC;
            """
            ,
            (rolling_from.isoformat(), rolling_to.isoformat()),
        ).fetchall()
        mode = f"rolling_{rolling_days}d"
        period_label = f"{rolling_from.isoformat()} -> {rolling_to.isoformat()}"
        window_from = rolling_from.isoformat()
        window_to = rolling_to.isoformat()
        coverage_target = rolling_days

    avg_sleep = _avg([r["sleep_hours"] for r in rows])
    avg_steps = _avg([r["steps"] for r in rows])
    avg_weight = _avg([r["weight_kg"] for r in rows])
    avg_whr = _avg([_row_whr(r) for r in rows])

    # Comparativa relativa contra periodo anterior equivalente
    previous_rows = []
    baseline_label = ""
    baseline_coverage_target = 0
    if use_range:
        from_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
        to_dt = datetime.strptime(date_to, "%Y-%m-%d").date()
        span_days = (to_dt - from_dt).days + 1
        prev_to = from_dt - timedelta(days=1)
        prev_from = prev_to - timedelta(days=max(0, span_days - 1))
        baseline_label = f"{prev_from.isoformat()} -> {prev_to.isoformat()}"
        baseline_coverage_target = span_days
        previous_rows = conn.execute(
            """
            SELECT log_date, sleep_hours, steps, weight_kg, waist_cm, hip_cm
            FROM diet_log
            WHERE log_date BETWEEN ? AND ?
            ORDER BY log_date ASC;
            """,
            (prev_from.isoformat(), prev_to.isoformat()),
        ).fetchall()
    else:
        today = datetime.now().date()
        prev_to = today - timedelta(days=rolling_days)
        prev_from = prev_to - timedelta(days=max(0, rolling_days - 1))
        baseline_label = f"{prev_from.isoformat()} -> {prev_to.isoformat()}"
        baseline_coverage_target = rolling_days
        previous_rows = conn.execute(
            """
            SELECT log_date, sleep_hours, steps, weight_kg, waist_cm, hip_cm
            FROM diet_log
            WHERE log_date BETWEEN ? AND ?
            ORDER BY log_date ASC;
            """
            ,
            (prev_from.isoformat(), prev_to.isoformat()),
        ).fetchall()

    prev_avg_sleep = _avg([r["sleep_hours"] for r in previous_rows])
    prev_avg_steps = _avg([r["steps"] for r in previous_rows])
    prev_avg_weight = _avg([r["weight_kg"] for r in previous_rows])
    prev_avg_whr = _avg([_row_whr(r) for r in previous_rows])

    def _diff(curr, prev):
        if curr is None or prev is None:
            return None
        return float(curr) - float(prev)

    weight_points = [(r["log_date"], r["weight_kg"]) for r in rows if r["weight_kg"] is not None]
    sleep_points = [(r["log_date"], r["sleep_hours"]) for r in rows if r["sleep_hours"] is not None]
    steps_points = [(r["log_date"], r["steps"]) for r in rows if r["steps"] is not None]
    whr_points = []
    for r in rows:
        whr = _row_whr(r)
        if whr is not None:
            whr_points.append((r["log_date"], whr))

    w_first, w_last = _first_last(weight_points)
    s_first, s_last = _first_last(sleep_points)
    p_first, p_last = _first_last(steps_points)
    h_first, h_last = _first_last(whr_points)

    delta_weight = None
    delta_sleep = None
    delta_steps = None
    delta_whr = None
    trend_dates = []
    trend_from = ""
    trend_to = ""

    if w_first and w_last:
        delta_weight = float(w_last[1]) - float(w_first[1])
        trend_dates.extend([w_first[0], w_last[0]])

    if s_first and s_last:
        delta_sleep = float(s_last[1]) - float(s_first[1])
        trend_dates.extend([s_first[0], s_last[0]])

    if p_first and p_last:
        delta_steps = float(p_last[1]) - float(p_first[1])
        trend_dates.extend([p_first[0], p_last[0]])

    if h_first and h_last:
        delta_whr = float(h_last[1]) - float(h_first[1])
        trend_dates.extend([h_first[0], h_last[0]])

    if trend_dates:
        trend_from = min(trend_dates)
        trend_to = max(trend_dates)

    trend_text, trend_tone = _trend_message(delta_weight, delta_whr)
    series_points = _summary_series(rows)

    return {
        "avg_sleep": avg_sleep,
        "avg_steps": avg_steps,
        "avg_weight": avg_weight,
        "avg_whr": avg_whr,
        "window_days": rolling_days,
        "mode": mode,
        "period_label": period_label,
        "date_from": date_from if use_range else window_from,
        "date_to": date_to if use_range else window_to,
        "coverage": {
            "current_count": len(rows),
            "current_target": coverage_target,
            "baseline_count": len(previous_rows),
            "baseline_target": baseline_coverage_target,
        },
        "trend": {
            "from": trend_from,
            "to": trend_to,
            "delta_weight": delta_weight,
            "delta_sleep": delta_sleep,
            "delta_steps": delta_steps,
            "delta_whr": delta_whr,
            "text": trend_text,
            "tone": trend_tone,
        },
        "relative": {
            "baseline_label": baseline_label if previous_rows else "",
            "sleep_delta": _diff(avg_sleep, prev_avg_sleep),
            "steps_delta": _diff(avg_steps, prev_avg_steps),
            "weight_delta": _diff(avg_weight, prev_avg_weight),
            "whr_delta": _diff(avg_whr, prev_avg_whr),
        },
        "series": {
            "points": series_points,
            "count": len(series_points),
        },
    }


def fetch_photo_gallery(
    conn,
    limit: int = 120,
    date_from: str = "",
    date_to: str = "",
):
    use_range = (
        valid_iso_date(date_from)
        and valid_iso_date(date_to)
        and str(date_from) <= str(date_to)
    )
    params = []
    where_parts = ["p.kind = 'progress'"]
    if use_range:
        where_parts.append("p.log_date BETWEEN ? AND ?")
        params.extend([date_from, date_to])

    params.append(int(limit))
    where_sql = " AND ".join(where_parts)
    rows = conn.execute(
        f"""
        SELECT
          p.log_date,
          p.path,
          p.original_name,
          d.weight_kg,
          d.waist_cm,
          d.hip_cm
        FROM photo_log p
        LEFT JOIN diet_log d ON d.log_date = p.log_date
        WHERE {where_sql}
        ORDER BY p.log_date DESC, p.created_at DESC
        LIMIT ?;
        """,
        tuple(params),
    ).fetchall()

    out = []
    for r in rows:
        photo_url = photo_url_from_rel(r["path"] or "")
        if not photo_url:
            continue
        out.append(
            {
                "log_date": r["log_date"],
                "photo_url": photo_url,
                "label": f"Foto {r['log_date']}",
                "original_name": r["original_name"] or "",
                "weight_kg": r["weight_kg"],
                "whr": (
                    float(r["waist_cm"]) / float(r["hip_cm"])
                    if r["waist_cm"] is not None and r["hip_cm"] not in (None, 0)
                    else None
                ),
            }
        )
    return out


def fetch_diet(conn, limit: int):
    window_days, window_from, window_to = resolve_calendar_window(conn, "diet", limit, fallback_to_today=True)
    if not window_from or not window_to:
        return []

    rows = conn.execute(
        """
        SELECT
          d.log_date, d.sleep_hours, d.sleep_quality, d.steps, d.weight_kg,
          d.waist_cm, d.hip_cm, d.alcohol_units,
          CASE
            WHEN EXISTS (
              SELECT 1
              FROM supplement_daily_log l
              JOIN supplement_catalog c ON c.supplement_id = l.supplement_id
              WHERE l.log_date = d.log_date
                AND LOWER(c.name) LIKE '%creatina%'
                AND COALESCE(l.doses_taken, 0) > 0
            ) THEN 'Y'
            WHEN d.creatine_yn IN ('Y','N') THEN d.creatine_yn
            ELSE NULL
          END AS creatine_yn,
          d.photo_yn,
          p.path AS photo_path
        FROM diet_log d
        LEFT JOIN photo_log p
          ON p.log_date = d.log_date AND p.kind = 'progress'
        WHERE d.log_date BETWEEN ? AND ?
        ORDER BY d.log_date DESC
        LIMIT ?;
        """,
        (window_from, window_to, window_days),
    ).fetchall()

    out = []
    for r in rows:
        out.append(
            {
                "log_date": r["log_date"],
                "sleep_hours": r["sleep_hours"],
                "sleep_quality": r["sleep_quality"],
                "steps": r["steps"],
                "weight_kg": r["weight_kg"],
                "waist_cm": r["waist_cm"],
                "hip_cm": r["hip_cm"],
                "alcohol_units": r["alcohol_units"] or 0,
                "creatine_yn": r["creatine_yn"],
                "photo_yn": r["photo_yn"],
                "photo_url": photo_url_from_rel(r["photo_path"] or ""),
            }
        )
    return out


def fetch_workout(conn, limit: int):
    _window_days, window_from, window_to = resolve_calendar_window(conn, "workout", limit, fallback_to_today=True)
    if not window_from or not window_to:
        return []

    rows = conn.execute(
        """
        SELECT
          s.session_id, s.log_date, s.session_order, s.session_done_yn, s.class_done,
          s.rpe_session, s.session_type, s.notes,
          e.exercise_id, e.exercise_name, e.set_order, e.weight_kg, e.reps, e.rpe, e.topset_text
        FROM workout_session s
        LEFT JOIN workout_exercise e ON e.session_id = s.session_id
        ORDER BY s.log_date ASC, s.session_order ASC, e.set_order ASC, e.exercise_id ASC;
        """,
    ).fetchall()

    sessions = []
    by_id = {}
    prev_by_exercise = {}

    for r in rows:
        session_id = r["session_id"]
        if session_id not in by_id:
            item = {
                "session_id": session_id,
                "log_date": r["log_date"],
                "session_order": r["session_order"],
                "session_done_yn": r["session_done_yn"],
                "session_type": r["session_type"] or "clase",
                "class_done": r["class_done"],
                "rpe_session": r["rpe_session"],
                "notes": r["notes"],
                "exercises": [],
            }
            by_id[session_id] = item
            sessions.append(item)

        if r["exercise_id"] is None:
            continue

        ex_name = (r["exercise_name"] or "").strip() or "Ejercicio"
        ex_key = ex_name.lower()
        prev = prev_by_exercise.get(ex_key, {})
        weight = r["weight_kg"]
        reps = r["reps"]
        delta_weight = (
            (float(weight) - float(prev["weight"]))
            if weight is not None and prev.get("weight") is not None
            else None
        )
        delta_reps = (
            (int(reps) - int(prev["reps"]))
            if reps is not None and prev.get("reps") is not None
            else None
        )
        if weight is not None or reps is not None:
            prev_by_exercise[ex_key] = {"weight": weight, "reps": reps}

        topset_text = r["topset_text"] or build_topset_text(weight, reps, r["rpe"])
        by_id[session_id]["exercises"].append(
            {
                "exercise_id": r["exercise_id"],
                "exercise_name": ex_name,
                "set_order": r["set_order"],
                "weight_kg": weight,
                "reps": reps,
                "rpe": r["rpe"],
                "topset_text": topset_text,
                "delta_weight": delta_weight,
                "delta_reps": delta_reps,
            }
        )

    windowed = [
        row for row in sessions
        if window_from <= str(row.get("log_date") or "") <= window_to
    ]
    out = list(reversed(windowed))
    for row in out:
        chunks = []
        for ex in row["exercises"]:
            text = ex["topset_text"] or build_topset_text(ex["weight_kg"], ex["reps"], ex["rpe"]) or "—"
            chunks.append(f"{ex['exercise_name']}: {text}")
        row["exercises_text"] = " | ".join(chunks)
    return out


def fetch_supplement_catalog(conn, include_inactive: bool = True):
    where = ""
    if not include_inactive:
        where = "WHERE c.active_yn = 'Y'"
    rows = conn.execute(
        f"""
        SELECT
          c.supplement_id,
          c.name,
          c.doses_per_day,
          c.active_yn,
          c.notes,
          c.created_at,
          c.updated_at
        FROM supplement_catalog c
        {where}
        ORDER BY c.active_yn DESC, c.name COLLATE NOCASE ASC, c.supplement_id ASC;
        """
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "supplement_id": r["supplement_id"],
                "name": r["name"],
                "doses_per_day": r["doses_per_day"],
                "active_yn": r["active_yn"] or "Y",
                "notes": r["notes"] or "",
                "created_at": r["created_at"] or "",
                "updated_at": r["updated_at"] or "",
            }
        )
    return out


def fetch_supplement_day(conn, log_date: str):
    rows = conn.execute(
        """
        SELECT
          c.supplement_id,
          c.name,
          c.doses_per_day,
          c.active_yn,
          l.doses_taken,
          l.notes
        FROM supplement_catalog c
        LEFT JOIN supplement_daily_log l
          ON l.supplement_id = c.supplement_id
         AND l.log_date = ?
        WHERE c.active_yn = 'Y' OR l.supplement_id IS NOT NULL
        ORDER BY c.active_yn DESC, c.name COLLATE NOCASE ASC, c.supplement_id ASC;
        """,
        (log_date,),
    ).fetchall()

    out = []
    target_total = 0
    taken_total = 0

    for r in rows:
        target = safe_int(r["doses_per_day"]) or 0
        taken = safe_int(r["doses_taken"])
        if taken is None:
            taken = 0
        target_total += max(target, 0)
        taken_total += max(taken, 0)
        out.append(
            {
                "supplement_id": r["supplement_id"],
                "name": r["name"],
                "doses_per_day": target,
                "active_yn": r["active_yn"] or "Y",
                "doses_taken": max(taken, 0),
                "notes": r["notes"] or "",
            }
        )

    adherence_pct = None
    if target_total > 0:
        adherence_pct = (taken_total / target_total) * 100.0

    has_logs = (
        conn.execute(
            "SELECT COUNT(*) AS n FROM supplement_daily_log WHERE log_date = ?;",
            (log_date,),
        ).fetchone()["n"]
        > 0
    )

    return {
        "log_date": log_date,
        "has_logs": has_logs,
        "entries": out,
        "totals": {
            "target_doses": target_total,
            "taken_doses": taken_total,
            "adherence_pct": adherence_pct,
        },
    }


def fetch_supplement_history(conn, limit: int = 15):
    lim, window_from, window_to = resolve_calendar_window(conn, "supplements", limit, fallback_to_today=True)
    if not window_from or not window_to:
        return []

    date_rows = conn.execute(
        """
        SELECT DISTINCT log_date
        FROM supplement_daily_log
        WHERE log_date BETWEEN ? AND ?
        ORDER BY log_date DESC
        LIMIT ?;
        """,
        (window_from, window_to, lim),
    ).fetchall()
    dates = [r["log_date"] for r in date_rows if r["log_date"]]
    if not dates:
        return []

    placeholders = ",".join(["?"] * len(dates))
    rows = conn.execute(
        f"""
        SELECT
          l.log_date,
          c.name,
          COALESCE(c.doses_per_day, 0) AS doses_per_day,
          COALESCE(l.doses_taken, 0) AS doses_taken,
          COALESCE(l.notes, '') AS notes
        FROM supplement_daily_log l
        JOIN supplement_catalog c ON c.supplement_id = l.supplement_id
        WHERE l.log_date IN ({placeholders})
        ORDER BY l.log_date DESC, c.name COLLATE NOCASE ASC;
        """,
        tuple(dates),
    ).fetchall()

    grouped = {}
    for date in dates:
        grouped[date] = {
            "log_date": date,
            "target_doses": 0,
            "taken_doses": 0,
            "detail_parts": [],
            "notes_parts": [],
        }

    for r in rows:
        date = r["log_date"]
        if date not in grouped:
            continue
        target = max(safe_int(r["doses_per_day"]) or 0, 0)
        taken = max(safe_int(r["doses_taken"]) or 0, 0)
        name = (r["name"] or "").strip() or "Suplemento"
        notes = (r["notes"] or "").strip()

        item = grouped[date]
        item["target_doses"] += target
        item["taken_doses"] += taken
        item["detail_parts"].append(f"{name} {taken}/{target}")
        if notes:
            item["notes_parts"].append(notes)

    out = []
    for date in dates:
        item = grouped[date]
        target = item["target_doses"]
        taken = item["taken_doses"]

        adherence_pct = None
        adherence_base_pct = None
        extra_doses = 0
        status = "muted"
        adherence_label = "Sin objetivo"

        if target > 0:
            adherence_pct = (taken / target) * 100.0
            base_ratio = min((taken / target), 1.0)
            adherence_base_pct = base_ratio * 100.0
            extra_doses = max(taken - target, 0)

            if taken >= target:
                status = "good"
                adherence_label = f"100% (+{extra_doses} extra)" if extra_doses > 0 else "100%"
            elif base_ratio >= 0.6:
                status = "warn"
                adherence_label = f"{adherence_base_pct:.0f}%"
            else:
                status = "bad"
                adherence_label = f"{adherence_base_pct:.0f}%"

        notes_unique = []
        for n in item["notes_parts"]:
            if n not in notes_unique:
                notes_unique.append(n)

        out.append(
            {
                "log_date": date,
                "target_doses": target,
                "taken_doses": taken,
                "adherence_pct": adherence_pct,
                "adherence_base_pct": adherence_base_pct,
                "adherence_label": adherence_label,
                "extra_doses": extra_doses,
                "status": status,
                "details": " · ".join(item["detail_parts"]),
                "notes": " | ".join(notes_unique),
            }
        )

    return out


def compute_plan_total_score(diet_score, workout_score):
    values = [v for v in (diet_score, workout_score) if v is not None]
    return (sum(values) / len(values)) if values else None


def fetch_plan_adherence_history(conn, log_date: str, window_days: int = 15):
    day = log_date if valid_iso_date(log_date) else today_iso()
    days = parse_plan_adherence_days(window_days, default=15)
    end_date = datetime.strptime(day, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=max(0, days - 1))

    rows = conn.execute(
        """
        SELECT log_date, diet_score, workout_score, notes, updated_at
        FROM plan_day_adherence
        WHERE log_date BETWEEN ? AND ?
        ORDER BY log_date DESC;
        """,
        (start_date.isoformat(), end_date.isoformat()),
    ).fetchall()

    items = []
    for row in rows:
        diet_score = row["diet_score"]
        workout_score = row["workout_score"]
        total_score = compute_plan_total_score(diet_score, workout_score)
        items.append(
            {
                "log_date": row["log_date"],
                "diet_score": diet_score,
                "workout_score": workout_score,
                "total_score": total_score,
                "notes": row["notes"] or "",
                "updated_at": row["updated_at"] or "",
            }
        )

    scored_days = sum(1 for item in items if item["total_score"] is not None)
    return {
        "window_days": days,
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "total_days": days,
        "logged_days": len(items),
        "scored_days": scored_days,
        "items": items,
    }


def fetch_plan_adherence_week_summary(conn, log_date: str):
    day = log_date if valid_iso_date(log_date) else today_iso()
    anchor = datetime.strptime(day, "%Y-%m-%d").date()
    week_start = anchor - timedelta(days=anchor.weekday())  # lunes
    week_end = week_start + timedelta(days=6)  # domingo

    rows = conn.execute(
        """
        SELECT log_date, diet_score, workout_score, notes, updated_at
        FROM plan_day_adherence
        WHERE log_date BETWEEN ? AND ?
        ORDER BY log_date ASC;
        """,
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    total_values = []
    diet_values = []
    workout_values = []
    for row in rows:
        diet_score = row["diet_score"]
        workout_score = row["workout_score"]
        total_score = compute_plan_total_score(diet_score, workout_score)
        if total_score is not None:
            total_values.append(float(total_score))
        if diet_score is not None:
            diet_values.append(float(diet_score))
        if workout_score is not None:
            workout_values.append(float(workout_score))

    def avg_or_none(values):
        return (sum(values) / len(values)) if values else None

    return {
        "from": week_start.isoformat(),
        "to": week_end.isoformat(),
        "total_days": 7,
        "logged_days": len(rows),
        "scored_days": len(total_values),
        "avg_total": avg_or_none(total_values),
        "avg_diet": avg_or_none(diet_values),
        "avg_workout": avg_or_none(workout_values),
    }


def fetch_plan_day(conn, log_date: str, adherence_days: int = 15):
    day = log_date if valid_iso_date(log_date) else today_iso()
    adherence_window_days = parse_plan_adherence_days(adherence_days, default=15)

    diet_row = conn.execute(
        """
        SELECT
          log_date, calories_target_kcal, protein_target_g, carbs_target_g, fat_target_g,
          breakfast, snack_1, lunch, snack_2, dinner, notes, source_tag, updated_at
        FROM plan_day_diet
        WHERE log_date = ?
        LIMIT 1;
        """,
        (day,),
    ).fetchone()

    session_rows = conn.execute(
        """
        SELECT
          s.log_date, s.plan_session_id, s.session_type, s.warmup, s.class_sessions,
          s.cardio, s.mobility_cooldown, s.additional_exercises, s.notes, s.source_tag,
          e.exercise_order, e.exercise_name, e.target_sets, e.target_reps_min, e.target_reps_max,
          e.target_weight_kg, e.target_rpe, e.intensity_target, e.progression_weight_rule, e.progression_reps_rule
        FROM plan_day_workout_session s
        LEFT JOIN plan_day_workout_exercise e
          ON e.log_date = s.log_date
         AND e.plan_session_id = s.plan_session_id
        WHERE s.log_date = ?
        ORDER BY s.plan_session_id ASC, e.exercise_order ASC;
        """,
        (day,),
    ).fetchall()

    sessions = []
    by_key = {}
    for r in session_rows:
        key = str(r["plan_session_id"] or "")
        if key not in by_key:
            item = {
                "log_date": r["log_date"],
                "plan_session_id": key,
                "session_type": r["session_type"] or "clase",
                "warmup": r["warmup"] or "",
                "class_sessions": r["class_sessions"] or "",
                "cardio": r["cardio"] or "",
                "mobility_cooldown": r["mobility_cooldown"] or "",
                "additional_exercises": r["additional_exercises"] or "",
                "notes": r["notes"] or "",
                "source_tag": r["source_tag"] or "",
                "exercises": [],
            }
            by_key[key] = item
            sessions.append(item)

        if r["exercise_order"] is None:
            continue
        by_key[key]["exercises"].append(
            {
                "exercise_order": r["exercise_order"],
                "exercise_name": r["exercise_name"] or "",
                "target_sets": r["target_sets"],
                "target_reps_min": r["target_reps_min"],
                "target_reps_max": r["target_reps_max"],
                "target_weight_kg": r["target_weight_kg"],
                "target_rpe": r["target_rpe"],
                "intensity_target": r["intensity_target"] or "",
                "progression_weight_rule": r["progression_weight_rule"] or "",
                "progression_reps_rule": r["progression_reps_rule"] or "",
            }
        )

    adherence_row = conn.execute(
        """
        SELECT log_date, diet_score, workout_score, notes, updated_at
        FROM plan_day_adherence
        WHERE log_date = ?
        LIMIT 1;
        """,
        (day,),
    ).fetchone()

    actual_diet = (
        conn.execute("SELECT 1 FROM diet_log WHERE log_date = ? LIMIT 1;", (day,)).fetchone()
        is not None
    )
    actual_workout_count = conn.execute(
        "SELECT COUNT(*) AS n FROM workout_session WHERE log_date = ?;",
        (day,),
    ).fetchone()["n"]

    diet_score = adherence_row["diet_score"] if adherence_row else None
    workout_score = adherence_row["workout_score"] if adherence_row else None
    total_score = compute_plan_total_score(diet_score, workout_score)
    adherence_history = fetch_plan_adherence_history(
        conn, day, window_days=adherence_window_days
    )
    adherence_week = fetch_plan_adherence_week_summary(conn, day)

    return {
        "log_date": day,
        "diet": (
            {
                "log_date": diet_row["log_date"],
                "calories_target_kcal": diet_row["calories_target_kcal"],
                "protein_target_g": diet_row["protein_target_g"],
                "carbs_target_g": diet_row["carbs_target_g"],
                "fat_target_g": diet_row["fat_target_g"],
                "breakfast": diet_row["breakfast"] or "",
                "snack_1": diet_row["snack_1"] or "",
                "lunch": diet_row["lunch"] or "",
                "snack_2": diet_row["snack_2"] or "",
                "dinner": diet_row["dinner"] or "",
                "notes": diet_row["notes"] or "",
                "source_tag": diet_row["source_tag"] or "",
                "updated_at": diet_row["updated_at"] or "",
            }
            if diet_row
            else None
        ),
        "workout_sessions": sessions,
        "actual": {
            "diet_logged": actual_diet,
            "workout_sessions_logged": int(actual_workout_count or 0),
        },
        "adherence": {
            "diet_score": diet_score,
            "workout_score": workout_score,
            "total_score": total_score,
            "notes": adherence_row["notes"] if adherence_row else "",
            "updated_at": adherence_row["updated_at"] if adherence_row else "",
        },
        "adherence_history": adherence_history,
        "adherence_week": adherence_week,
        "coverage": {
            "has_diet_plan": diet_row is not None,
            "has_workout_plan": len(sessions) > 0,
        },
    }


def build_state(
    limit: int,
    date_from: str = "",
    date_to: str = "",
    summary_days: int = 7,
):
    limit = int(limit) if str(limit).isdigit() else 15
    summary_days = parse_summary_days(summary_days, default=7)
    plan_date = today_iso()
    with _conn() as conn:
        return {
            "summary": fetch_summary(
                conn,
                date_from=date_from,
                date_to=date_to,
                rolling_days=summary_days,
            ),
            "diet": fetch_diet(conn, limit),
            "workout": fetch_workout(conn, limit),
            "photos": fetch_photo_gallery(
                conn,
                limit=max(40, limit * 3),
                date_from=date_from,
                date_to=date_to,
            ),
            "plan_today": fetch_plan_day(conn, plan_date),
        }


def count_upload_files() -> int:
    root = Path(UPLOAD_ROOT)
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def create_db_snapshot(snapshot_path: Path):
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as src, closing(sqlite3.connect(snapshot_path)) as dst:
        src.backup(dst)


def is_safe_backup_member(member_name: str) -> bool:
    raw = str(member_name or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or raw.endswith("/"):
        return False
    norm = os.path.normpath(raw).replace("\\", "/")
    if norm.startswith("../") or norm == "..":
        return False
    if "/../" in f"/{norm}/":
        return False
    return True


@APP.context_processor
def inject_auth_context():
    return {"auth_enabled": auth_enabled(), "csrf_token": ensure_csrf_token()}


def ensure_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or len(token) < 16:
        token = secrets.token_hex(32)
        session[CSRF_SESSION_KEY] = token
    return token


def request_csrf_token() -> str:
    header_token = str(request.headers.get("X-CSRF-Token") or "").strip()
    if header_token:
        return header_token
    form_token = str(request.form.get("csrf_token") or "").strip()
    if form_token:
        return form_token
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        if isinstance(payload, dict):
            return str(payload.get("csrf_token") or "").strip()
    return ""


@APP.before_request
def csrf_protect():
    # Keep a per-session token ready for all rendered pages/forms.
    expected = ensure_csrf_token()
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return None

    received = request_csrf_token()
    if received and hmac.compare_digest(expected, received):
        return None
    return jsonify({"ok": False, "error": "CSRF token inválido."}), 403


@APP.before_request
def require_local_auth():
    if not auth_enabled():
        return None

    endpoint = request.endpoint
    if endpoint is None:
        return None

    if endpoint in {"static", "login_page", "login_submit"}:
        return None

    if is_authenticated():
        return None

    return unauthorized_response()


# -----------------------------
# Routes (pages)
# -----------------------------
@APP.get("/login")
def login_page():
    if not auth_enabled():
        return redirect(url_for("index"))
    if is_authenticated():
        nxt = safe_next_path(request.args.get("next"))
        return redirect(nxt)
    return render_template("login.html", error="", next_path=safe_next_path(request.args.get("next")))


@APP.post("/login")
def login_submit():
    if not auth_enabled():
        return redirect(url_for("index"))

    password = request.form.get("password", "")
    next_path = safe_next_path(request.form.get("next") or request.args.get("next"))
    if password and check_password_hash(AUTH_PASSWORD_HASH, password):
        session.clear()
        session["auth_ok"] = True
        session[CSRF_SESSION_KEY] = secrets.token_hex(32)
        return redirect(next_path)

    return (
        render_template(
            "login.html",
            error="Clave incorrecta. Intenta de nuevo.",
            next_path=next_path,
        ),
        401,
    )


@APP.post("/logout")
def logout_submit():
    session.clear()
    return jsonify({"ok": True})


@APP.get("/")
def index():
    summary_days = parse_summary_days(request.args.get("summary_days"), default=7)
    state = build_state(limit=15, summary_days=summary_days)
    return render_template("index.html", state=state)


@APP.get("/portada")
def cover_page():
    return render_template("cover.html")


@APP.get("/help")
def help_page():
    return render_template("help.html")


@APP.get("/changelog")
def changelog_page():
    return render_template("changelog.html")


# -----------------------------
# Routes (API)
# -----------------------------
@APP.get("/api/state")
def api_state():
    limit = request.args.get("limit", "15")
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    summary_days = parse_summary_days(request.args.get("summary_days"), default=7)
    state = build_state(
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        summary_days=summary_days,
    )
    return jsonify(state)


@APP.get("/api/supplements/history")
def api_supplements_history_get():
    limit = safe_int(request.args.get("limit"))
    if limit is None:
        limit = 15
    if limit < 1:
        return jsonify({"ok": False, "error": "limit invalido"}), 400
    with _conn() as conn:
        rows = fetch_supplement_history(conn, limit=limit)
    return jsonify({"ok": True, "limit": limit, "rows": rows})


@APP.get("/api/supplements/config")
def api_supplements_config_get():
    include_inactive = not truthy(request.args.get("active_only"))
    with _conn() as conn:
        rows = fetch_supplement_catalog(conn, include_inactive=include_inactive)
    return jsonify({"ok": True, "supplements": rows})


@APP.post("/api/supplements/config")
def api_supplements_config_post():
    data = request.get_json(silent=True) or {}
    supplement_id = safe_int(data.get("supplement_id"))
    name = normalize_supplement_name(data.get("name"))
    doses_per_day = safe_int(data.get("doses_per_day"))
    active_yn = yes_no(data.get("active_yn"), default="Y")
    notes = str(data.get("notes") or "").strip()[:240]
    now_iso = datetime.now().replace(microsecond=0).isoformat()

    if not name:
        return jsonify({"ok": False, "error": "Nombre de suplemento requerido."}), 400
    if doses_per_day is None:
        return jsonify({"ok": False, "error": "Define cuantas tomas al dia (numero entero)."}), 400
    if doses_per_day < 1 or doses_per_day > 12:
        return jsonify({"ok": False, "error": "Las tomas por dia deben estar entre 1 y 12."}), 400

    with _conn() as conn:
        conflict = conn.execute(
            """
            SELECT supplement_id
            FROM supplement_catalog
            WHERE name = ? COLLATE NOCASE
              AND (? IS NULL OR supplement_id <> ?)
            LIMIT 1;
            """,
            (name, supplement_id, supplement_id),
        ).fetchone()
        if conflict:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Ya existe un suplemento con ese nombre.",
                    }
                ),
                409,
            )

        if supplement_id is None:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO supplement_catalog (
                      name, doses_per_day, active_yn, notes, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        name,
                        doses_per_day,
                        active_yn,
                        notes or None,
                        now_iso,
                        now_iso,
                    ),
                )
            except sqlite3.IntegrityError:
                return jsonify({"ok": False, "error": "Ya existe un suplemento con ese nombre."}), 409
            target_id = int(cur.lastrowid)
            mode = "create"
        else:
            current = conn.execute(
                "SELECT supplement_id FROM supplement_catalog WHERE supplement_id = ? LIMIT 1;",
                (supplement_id,),
            ).fetchone()
            if not current:
                return jsonify({"ok": False, "error": "Suplemento no encontrado."}), 404
            conn.execute(
                """
                UPDATE supplement_catalog
                SET
                  name = ?,
                  doses_per_day = ?,
                  active_yn = ?,
                  notes = ?,
                  updated_at = ?
                WHERE supplement_id = ?;
                """,
                (
                    name,
                    doses_per_day,
                    active_yn,
                    notes or None,
                    now_iso,
                    supplement_id,
                ),
            )
            target_id = int(supplement_id)
            mode = "edit"
        conn.commit()

        row = conn.execute(
            """
            SELECT
              supplement_id, name, doses_per_day, active_yn, notes, created_at, updated_at
            FROM supplement_catalog
            WHERE supplement_id = ?
            LIMIT 1;
            """,
            (target_id,),
        ).fetchone()

    return jsonify(
        {
            "ok": True,
            "entry_mode": mode,
            "supplement": {
                "supplement_id": row["supplement_id"],
                "name": row["name"],
                "doses_per_day": row["doses_per_day"],
                "active_yn": row["active_yn"] or "Y",
                "notes": row["notes"] or "",
                "created_at": row["created_at"] or "",
                "updated_at": row["updated_at"] or "",
            },
        }
    )


@APP.delete("/api/supplements/config/<int:supplement_id>")
def api_supplements_config_delete(supplement_id: int):
    sid = int(supplement_id)
    with _conn() as conn:
        row = conn.execute(
            "SELECT supplement_id, name FROM supplement_catalog WHERE supplement_id = ? LIMIT 1;",
            (sid,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Suplemento no encontrado."}), 404
        conn.execute("DELETE FROM supplement_catalog WHERE supplement_id = ?;", (sid,))
        conn.commit()
    return jsonify({"ok": True, "supplement_id": sid, "name": row["name"]})


@APP.get("/api/supplements/day")
def api_supplements_day_get():
    log_date = (request.args.get("log_date") or "").strip() or today_iso()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400
    with _conn() as conn:
        day = fetch_supplement_day(conn, log_date)
    return jsonify({"ok": True, **day})


@APP.post("/api/supplements/day")
def api_supplements_day_post():
    data = request.get_json(silent=True) or {}
    log_date = (data.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400

    entries = data.get("entries")
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        return jsonify({"ok": False, "error": "entries debe ser una lista."}), 400

    cleaned = []
    seen = set()
    for item in entries:
        if not isinstance(item, dict):
            return jsonify({"ok": False, "error": "Formato de entries invalido."}), 400
        sid = safe_int(item.get("supplement_id"))
        if sid is None or sid < 1:
            return jsonify({"ok": False, "error": "supplement_id invalido en entries."}), 400
        if sid in seen:
            return jsonify({"ok": False, "error": "Hay suplementos repetidos en entries."}), 400
        seen.add(sid)

        doses_taken = safe_int(item.get("doses_taken"))
        if doses_taken is None:
            doses_taken = 0
        if doses_taken < 0 or doses_taken > 24:
            return jsonify({"ok": False, "error": "doses_taken debe estar entre 0 y 24."}), 400
        notes = str(item.get("notes") or "").strip()[:240]
        cleaned.append((sid, doses_taken, notes or None))

    now_iso = datetime.now().replace(microsecond=0).isoformat()
    with _conn() as conn:
        known_ids = {
            r["supplement_id"]
            for r in conn.execute(
                "SELECT supplement_id FROM supplement_catalog WHERE supplement_id IN (%s);"
                % ",".join(["?"] * len(cleaned)),
                tuple(item[0] for item in cleaned),
            ).fetchall()
        } if cleaned else set()

        for sid, _doses_taken, _notes in cleaned:
            if sid not in known_ids:
                return jsonify({"ok": False, "error": f"Suplemento no encontrado (ID {sid})."}), 404

        conn.execute("DELETE FROM supplement_daily_log WHERE log_date = ?;", (log_date,))
        if cleaned:
            batch_rows = [
                (
                    log_date,
                    sid,
                    doses_taken,
                    notes,
                    now_iso,
                    now_iso,
                )
                for sid, doses_taken, notes in cleaned
            ]
            conn.executemany(
                """
                INSERT INTO supplement_daily_log (
                  log_date, supplement_id, doses_taken, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                batch_rows,
            )
        conn.commit()
        day = fetch_supplement_day(conn, log_date)

    return jsonify({"ok": True, **day})


@APP.delete("/api/supplements/day/<log_date>")
def api_supplements_day_delete(log_date: str):
    date = (log_date or "").strip()
    if not valid_iso_date(date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400
    with _conn() as conn:
        result = conn.execute(
            "DELETE FROM supplement_daily_log WHERE log_date = ?;",
            (date,),
        )
        conn.commit()
    deleted = int(result.rowcount or 0)
    if deleted == 0:
        return jsonify({"ok": False, "error": "No hay registro para esa fecha."}), 404
    return jsonify({"ok": True, "log_date": date, "deleted_rows": deleted})


@APP.get("/api/plan/day")
def api_plan_day_get():
    log_date = (request.args.get("log_date") or "").strip() or today_iso()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400
    adherence_days = parse_plan_adherence_days(
        request.args.get("adherence_days"), default=15
    )
    with _conn() as conn:
        payload = fetch_plan_day(conn, log_date, adherence_days=adherence_days)
    return jsonify({"ok": True, **payload})


@APP.post("/api/plan/adherence")
def api_plan_adherence_post():
    data = request.get_json(silent=True) or {}
    log_date = (data.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400

    raw_diet_score = data.get("diet_score")
    raw_workout_score = data.get("workout_score")
    diet_score = parse_plan_score(raw_diet_score)
    workout_score = parse_plan_score(raw_workout_score)
    notes = _clip_text(data.get("notes"), 300)

    if raw_diet_score not in (None, "") and diet_score is None:
        return jsonify({"ok": False, "error": "diet_score debe ser 1, 0.5 o 0."}), 400
    if raw_workout_score not in (None, "") and workout_score is None:
        return jsonify({"ok": False, "error": "workout_score debe ser 1, 0.5 o 0."}), 400

    with _conn() as conn:
        if diet_score is None and workout_score is None and not notes:
            conn.execute("DELETE FROM plan_day_adherence WHERE log_date = ?;", (log_date,))
        else:
            conn.execute(
                """
                INSERT INTO plan_day_adherence (log_date, diet_score, workout_score, notes, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(log_date) DO UPDATE SET
                  diet_score=excluded.diet_score,
                  workout_score=excluded.workout_score,
                  notes=excluded.notes,
                  updated_at=excluded.updated_at;
                """,
                (
                    log_date,
                    diet_score,
                    workout_score,
                    notes or None,
                    datetime.now().replace(microsecond=0).isoformat(),
                ),
            )
        conn.commit()
        payload = fetch_plan_day(conn, log_date)
    return jsonify({"ok": True, **payload})


@APP.post("/api/plan/import/diet")
def api_plan_import_diet():
    file_storage = request.files.get("file")
    if not file_storage or not getattr(file_storage, "filename", ""):
        return jsonify({"ok": False, "error": "Debes subir un archivo CSV."}), 400

    filename = str(file_storage.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        return jsonify({"ok": False, "error": "El archivo debe tener extension .csv."}), 400

    source_tag = _clip_text(request.form.get("source_tag") or "manual", 80)
    try:
        text = read_text_file_storage(file_storage)
        rows = parse_plan_csv_rows(
            text,
            canonical_header_fn=canonical_plan_diet_header,
            required_fields=PLAN_DIET_REQUIRED,
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo leer el CSV."}), 400

    seen_dates = set()
    summary = {"total": len(rows), "imported": 0, "invalid": 0}
    results = []
    now_iso = datetime.now().replace(microsecond=0).isoformat()

    with _conn() as conn:
        for line_no, row in rows:
            normalized, errors = parse_plan_diet_row(row)
            log_date = normalized.get("log_date") or ""
            if log_date and log_date in seen_dates:
                errors.append("date duplicada dentro del CSV")

            if errors:
                summary["invalid"] += 1
                results.append(
                    {
                        "row_number": line_no,
                        "status": "invalid",
                        "reason": "; ".join(errors),
                        "row": normalized,
                    }
                )
                if log_date:
                    seen_dates.add(log_date)
                continue

            conn.execute(
                """
                INSERT INTO plan_day_diet (
                  log_date, calories_target_kcal, protein_target_g, carbs_target_g, fat_target_g,
                  breakfast, snack_1, lunch, snack_2, dinner, notes, source_tag, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(log_date) DO UPDATE SET
                  calories_target_kcal=excluded.calories_target_kcal,
                  protein_target_g=excluded.protein_target_g,
                  carbs_target_g=excluded.carbs_target_g,
                  fat_target_g=excluded.fat_target_g,
                  breakfast=excluded.breakfast,
                  snack_1=excluded.snack_1,
                  lunch=excluded.lunch,
                  snack_2=excluded.snack_2,
                  dinner=excluded.dinner,
                  notes=excluded.notes,
                  source_tag=excluded.source_tag,
                  updated_at=excluded.updated_at;
                """,
                (
                    normalized["log_date"],
                    normalized["calories_target_kcal"],
                    normalized["protein_target_g"],
                    normalized["carbs_target_g"],
                    normalized["fat_target_g"],
                    normalized["breakfast"],
                    normalized["snack_1"],
                    normalized["lunch"],
                    normalized["snack_2"],
                    normalized["dinner"],
                    normalized["notes"] or None,
                    source_tag or "manual",
                    now_iso,
                    now_iso,
                ),
            )
            seen_dates.add(log_date)
            summary["imported"] += 1
            results.append(
                {
                    "row_number": line_no,
                    "status": "imported",
                    "reason": "",
                    "row": normalized,
                }
            )
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "summary": summary,
            "results": results,
            "accepted_columns": list(PLAN_DIET_FIELDS),
        }
    )


def _plan_session_id_from_order(order: int) -> str:
    return f"S{int(order):02d}"


@APP.post("/api/plan/import/workout")
def api_plan_import_workout_combined():
    file_storage = request.files.get("file")
    if not file_storage or not getattr(file_storage, "filename", ""):
        return jsonify({"ok": False, "error": "Debes subir un archivo CSV."}), 400

    filename = str(file_storage.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        return jsonify({"ok": False, "error": "El archivo debe tener extension .csv."}), 400

    source_tag = _clip_text(request.form.get("source_tag") or "manual", 80)
    try:
        text = read_text_file_storage(file_storage)
        rows = parse_plan_csv_rows(
            text,
            canonical_header_fn=canonical_plan_workout_combined_header,
            required_fields=PLAN_WORKOUT_COMBINED_REQUIRED,
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo leer el CSV."}), 400

    summary = {"total": len(rows), "imported": 0, "invalid": 0, "warned": 0}
    results = []
    now_iso = datetime.now().replace(microsecond=0).isoformat()
    order_by_date = {}
    seen_keys = set()

    with _conn() as conn:
        for line_no, row in rows:
            normalized, errors, warnings = parse_plan_workout_combined_row(row)

            log_date = normalized.get("log_date") or ""
            if log_date:
                order_by_date[log_date] = order_by_date.get(log_date, 0) + 1
                session_order = order_by_date[log_date]
                plan_session_id = _plan_session_id_from_order(session_order)
            else:
                session_order = None
                plan_session_id = ""

            normalized["session_order"] = session_order
            normalized["plan_session_id"] = plan_session_id
            key = (log_date, plan_session_id)

            if log_date and plan_session_id and key in seen_keys:
                errors.append("date + session_order duplicados dentro del CSV")

            if errors:
                summary["invalid"] += 1
                results.append(
                    {
                        "row_number": line_no,
                        "status": "invalid",
                        "reason": "; ".join(errors),
                        "row": normalized,
                    }
                )
                if log_date and plan_session_id:
                    seen_keys.add(key)
                continue

            conn.execute(
                """
                INSERT INTO plan_day_workout_session (
                  log_date, plan_session_id, session_type, warmup, class_sessions, cardio,
                  mobility_cooldown, additional_exercises, notes, source_tag, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(log_date, plan_session_id) DO UPDATE SET
                  session_type=excluded.session_type,
                  warmup=excluded.warmup,
                  class_sessions=excluded.class_sessions,
                  cardio=excluded.cardio,
                  mobility_cooldown=excluded.mobility_cooldown,
                  additional_exercises=excluded.additional_exercises,
                  notes=excluded.notes,
                  source_tag=excluded.source_tag,
                  updated_at=excluded.updated_at;
                """,
                (
                    log_date,
                    plan_session_id,
                    normalized["session_type"],
                    normalized["warmup"] or None,
                    normalized["class_sessions"] or None,
                    normalized["cardio"] or None,
                    normalized["mobility_cooldown"] or None,
                    normalized["additional_exercises"] or None,
                    normalized["notes"] or None,
                    source_tag or "manual",
                    now_iso,
                    now_iso,
                ),
            )

            conn.execute(
                "DELETE FROM plan_day_workout_exercise WHERE log_date = ? AND plan_session_id = ?;",
                (log_date, plan_session_id),
            )
            for ex in normalized.get("exercises", []):
                conn.execute(
                    """
                    INSERT INTO plan_day_workout_exercise (
                      log_date, plan_session_id, exercise_order, exercise_name,
                      target_sets, target_reps_min, target_reps_max, target_weight_kg, target_rpe,
                      intensity_target, progression_weight_rule, progression_reps_rule, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        log_date,
                        plan_session_id,
                        ex["exercise_order"],
                        ex["exercise_name"],
                        ex["target_sets"],
                        ex["target_reps_min"],
                        ex["target_reps_max"],
                        ex["target_weight_kg"],
                        ex["target_rpe"],
                        ex["intensity_target"] or None,
                        ex["progression_weight_rule"] or None,
                        ex["progression_reps_rule"] or None,
                        now_iso,
                        now_iso,
                    ),
                )

            summary["imported"] += 1
            if warnings:
                summary["warned"] += 1
            seen_keys.add(key)
            results.append(
                {
                    "row_number": line_no,
                    "status": "imported",
                    "reason": " | ".join(warnings),
                    "row": normalized,
                }
            )
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "summary": summary,
            "results": results,
            "accepted_columns": list(PLAN_WORKOUT_COMBINED_FIELDS),
        }
    )


@APP.post("/api/plan/import/workout-sessions")
def api_plan_import_workout_sessions():
    file_storage = request.files.get("file")
    if not file_storage or not getattr(file_storage, "filename", ""):
        return jsonify({"ok": False, "error": "Debes subir un archivo CSV."}), 400

    filename = str(file_storage.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        return jsonify({"ok": False, "error": "El archivo debe tener extension .csv."}), 400

    source_tag = _clip_text(request.form.get("source_tag") or "manual", 80)
    try:
        text = read_text_file_storage(file_storage)
        rows = parse_plan_csv_rows(
            text,
            canonical_header_fn=canonical_plan_workout_session_header,
            required_fields=PLAN_WORKOUT_SESSION_REQUIRED,
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo leer el CSV."}), 400

    summary = {"total": len(rows), "imported": 0, "invalid": 0}
    results = []
    seen_keys = set()
    now_iso = datetime.now().replace(microsecond=0).isoformat()

    with _conn() as conn:
        for line_no, row in rows:
            normalized, errors = parse_plan_workout_session_row(row)
            key = (normalized.get("log_date"), normalized.get("plan_session_id"))
            if key[0] and key[1] and key in seen_keys:
                errors.append("date + session_id duplicados dentro del CSV")

            if errors:
                summary["invalid"] += 1
                results.append(
                    {
                        "row_number": line_no,
                        "status": "invalid",
                        "reason": "; ".join(errors),
                        "row": normalized,
                    }
                )
                if key[0] and key[1]:
                    seen_keys.add(key)
                continue

            conn.execute(
                """
                INSERT INTO plan_day_workout_session (
                  log_date, plan_session_id, session_type, warmup, class_sessions, cardio,
                  mobility_cooldown, additional_exercises, notes, source_tag, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(log_date, plan_session_id) DO UPDATE SET
                  session_type=excluded.session_type,
                  warmup=excluded.warmup,
                  class_sessions=excluded.class_sessions,
                  cardio=excluded.cardio,
                  mobility_cooldown=excluded.mobility_cooldown,
                  additional_exercises=excluded.additional_exercises,
                  notes=excluded.notes,
                  source_tag=excluded.source_tag,
                  updated_at=excluded.updated_at;
                """,
                (
                    normalized["log_date"],
                    normalized["plan_session_id"],
                    normalized["session_type"],
                    normalized["warmup"] or None,
                    normalized["class_sessions"] or None,
                    normalized["cardio"] or None,
                    normalized["mobility_cooldown"] or None,
                    normalized["additional_exercises"] or None,
                    normalized["notes"] or None,
                    source_tag or "manual",
                    now_iso,
                    now_iso,
                ),
            )
            seen_keys.add(key)
            summary["imported"] += 1
            results.append(
                {
                    "row_number": line_no,
                    "status": "imported",
                    "reason": "",
                    "row": normalized,
                }
            )
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "summary": summary,
            "results": results,
            "accepted_columns": list(PLAN_WORKOUT_SESSION_FIELDS),
        }
    )


@APP.post("/api/plan/import/workout-exercises")
def api_plan_import_workout_exercises():
    file_storage = request.files.get("file")
    if not file_storage or not getattr(file_storage, "filename", ""):
        return jsonify({"ok": False, "error": "Debes subir un archivo CSV."}), 400

    filename = str(file_storage.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        return jsonify({"ok": False, "error": "El archivo debe tener extension .csv."}), 400

    try:
        text = read_text_file_storage(file_storage)
        rows = parse_plan_csv_rows(
            text,
            canonical_header_fn=canonical_plan_workout_exercise_header,
            required_fields=PLAN_WORKOUT_EXERCISE_REQUIRED,
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo leer el CSV."}), 400

    summary = {"total": len(rows), "imported": 0, "invalid": 0}
    results = []
    valid_rows = []
    seen_keys = set()

    for line_no, row in rows:
        normalized, errors = parse_plan_workout_exercise_row(row)
        key = (
            normalized.get("log_date"),
            normalized.get("plan_session_id"),
            normalized.get("exercise_order"),
        )
        if key[0] and key[1] and key[2] is not None and key in seen_keys:
            errors.append("date + session_id + exercise_order duplicados en CSV")
        if errors:
            summary["invalid"] += 1
            results.append(
                {
                    "row_number": line_no,
                    "status": "invalid",
                    "reason": "; ".join(errors),
                    "row": normalized,
                }
            )
            if key[0] and key[1] and key[2] is not None:
                seen_keys.add(key)
            continue
        seen_keys.add(key)
        valid_rows.append((line_no, normalized))

    now_iso = datetime.now().replace(microsecond=0).isoformat()
    with _conn() as conn:
        session_keys = sorted(
            {
                (row["log_date"], row["plan_session_id"])
                for _line_no, row in valid_rows
                if row.get("log_date") and row.get("plan_session_id")
            }
        )
        if session_keys:
            placeholders = ",".join(["(?, ?)"] * len(session_keys))
            flat = []
            for d, sid in session_keys:
                flat.extend([d, sid])
            known_session_keys = {
                (r["log_date"], r["plan_session_id"])
                for r in conn.execute(
                    f"""
                    SELECT log_date, plan_session_id
                    FROM plan_day_workout_session
                    WHERE (log_date, plan_session_id) IN ({placeholders});
                    """,
                    tuple(flat),
                ).fetchall()
            }
        else:
            known_session_keys = set()

        missing_idx = set()
        for idx, (line_no, row) in enumerate(valid_rows):
            key = (row.get("log_date"), row.get("plan_session_id"))
            if key not in known_session_keys:
                summary["invalid"] += 1
                results.append(
                    {
                        "row_number": line_no,
                        "status": "invalid",
                        "reason": "No existe la sesión en plan_day_workout_session (importa primero workout-sessions).",
                        "row": row,
                    }
                )
                missing_idx.add(idx)

        final_rows = [x for i, x in enumerate(valid_rows) if i not in missing_idx]
        touched_sessions = sorted({(r["log_date"], r["plan_session_id"]) for _, r in final_rows})
        for log_date, session_id in touched_sessions:
            conn.execute(
                "DELETE FROM plan_day_workout_exercise WHERE log_date = ? AND plan_session_id = ?;",
                (log_date, session_id),
            )

        for line_no, row in final_rows:
            conn.execute(
                """
                INSERT INTO plan_day_workout_exercise (
                  log_date, plan_session_id, exercise_order, exercise_name,
                  target_sets, target_reps_min, target_reps_max, target_weight_kg, target_rpe,
                  intensity_target, progression_weight_rule, progression_reps_rule, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    row["log_date"],
                    row["plan_session_id"],
                    row["exercise_order"],
                    row["exercise_name"],
                    row["target_sets"],
                    row["target_reps_min"],
                    row["target_reps_max"],
                    row["target_weight_kg"],
                    row["target_rpe"],
                    row["intensity_target"] or None,
                    row["progression_weight_rule"] or None,
                    row["progression_reps_rule"] or None,
                    now_iso,
                    now_iso,
                ),
            )
            summary["imported"] += 1
            results.append(
                {
                    "row_number": line_no,
                    "status": "imported",
                    "reason": "",
                    "row": row,
                }
            )
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "summary": summary,
            "results": sorted(results, key=lambda x: (x.get("row_number") or 0)),
            "accepted_columns": list(PLAN_WORKOUT_EXERCISE_FIELDS),
        }
    )


@APP.delete("/api/plan/diet/<log_date>")
def api_plan_diet_delete_day(log_date: str):
    day = (log_date or "").strip()
    if not valid_iso_date(day):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400

    with _conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM plan_day_diet WHERE log_date = ? LIMIT 1;",
            (day,),
        ).fetchone()
        if not exists:
            return jsonify({"ok": False, "error": "No existe dieta plan para esa fecha."}), 404
        deleted_rows = conn.execute(
            "DELETE FROM plan_day_diet WHERE log_date = ?;",
            (day,),
        ).rowcount
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "log_date": day,
            "deleted_rows": int(deleted_rows or 0),
        }
    )


@APP.delete("/api/plan/diet")
def api_plan_diet_flush():
    with _conn() as conn:
        total_rows = conn.execute(
            "SELECT COUNT(*) AS n FROM plan_day_diet;",
        ).fetchone()["n"]
        conn.execute("DELETE FROM plan_day_diet;")
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "deleted_rows": int(total_rows or 0),
        }
    )


@APP.delete("/api/plan/workout/<log_date>/<plan_session_id>")
def api_plan_workout_delete_session(log_date: str, plan_session_id: str):
    day = (log_date or "").strip()
    if not valid_iso_date(day):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400

    session_id = _clip_text(plan_session_id, 48)
    if not session_id:
        return jsonify({"ok": False, "error": "plan_session_id invalido"}), 400

    with _conn() as conn:
        exists = conn.execute(
            """
            SELECT 1
            FROM plan_day_workout_session
            WHERE log_date = ? AND plan_session_id = ?
            LIMIT 1;
            """,
            (day, session_id),
        ).fetchone()
        if not exists:
            return jsonify({"ok": False, "error": "No existe esa sesion planificada."}), 404

        deleted_exercises = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM plan_day_workout_exercise
            WHERE log_date = ? AND plan_session_id = ?;
            """,
            (day, session_id),
        ).fetchone()["n"]
        deleted_sessions = conn.execute(
            """
            DELETE FROM plan_day_workout_session
            WHERE log_date = ? AND plan_session_id = ?;
            """,
            (day, session_id),
        ).rowcount
        conn.commit()

    return jsonify(
        {
            "ok": True,
            "log_date": day,
            "plan_session_id": session_id,
            "deleted_sessions": int(deleted_sessions or 0),
            "deleted_exercises": int(deleted_exercises or 0),
        }
    )


@APP.delete("/api/plan/workout")
def api_plan_workout_flush():
    with _conn() as conn:
        counts = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM plan_day_workout_session) AS sessions,
              (SELECT COUNT(*) FROM plan_day_workout_exercise) AS exercises;
            """
        ).fetchone()
        conn.execute("DELETE FROM plan_day_workout_session;")
        conn.commit()
    deleted_sessions = int(counts["sessions"] if counts else 0)
    deleted_exercises = int(counts["exercises"] if counts else 0)

    return jsonify(
        {
            "ok": True,
            "deleted_sessions": deleted_sessions,
            "deleted_exercises": deleted_exercises,
        }
    )


@APP.post("/api/diet")
def api_diet():
    # multipart (foto) o json (sin foto)
    ctype = (request.content_type or "").lower()
    is_multipart = "multipart/form-data" in ctype
    max_len = APP.config.get("MAX_CONTENT_LENGTH")
    if max_len and request.content_length and request.content_length > max_len:
        max_mb = int(max_len / (1024 * 1024))
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"Archivo demasiado grande. Máximo permitido: {max_mb} MB.",
                }
            ),
            413,
        )

    if is_multipart:
        data = dict(request.form or {})
        photo = request.files.get("photo")
    else:
        data = request.get_json(silent=True) or {}
        photo = None

    log_date = (data.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date inválida"}), 400

    sleep_hours = safe_float(data.get("sleep_hours"))
    sleep_quality = safe_int(data.get("sleep_quality"))
    steps = safe_int(data.get("steps"))
    weight_kg = safe_float(data.get("weight_kg"))
    waist_cm = safe_float(data.get("waist_cm"))
    hip_cm = safe_float(data.get("hip_cm"))
    alcohol_units = safe_int(data.get("alcohol_units")) or 0
    creatine_yn = yn_or_none(data.get("creatine_yn"))
    photo_yn = yn_or_none(data.get("photo_yn"))
    photo_replace_confirm = truthy(data.get("photo_replace_confirm"))
    mode = entry_mode(data.get("entry_mode"))

    with _conn() as conn:
        exists_day = (
            conn.execute(
                "SELECT 1 FROM diet_log WHERE log_date = ? LIMIT 1;",
                (log_date,),
            ).fetchone()
            is not None
        )
    if mode == "create" and exists_day:
        return (
            jsonify(
                {
                    "ok": False,
                    "needs_edit": True,
                    "log_date": log_date,
                    "message": "Ese día ya existe. Si quieres cambiarlo, edítalo desde la tabla.",
                }
            ),
            409,
        )

    # Si la UI envía N explícito, respétalo; si llega vacío => NULL
    # (alcohol se mantiene en 0 por diseño)
    saved_photo_rel = ""
    photo_original_name = ""

    # Refuerzo backend: si ya hay foto para la misma fecha/kind, exige confirmación explícita
    if photo and getattr(photo, "filename", ""):
        with _conn() as conn:
            existing_rel = get_existing_photo_rel(conn, log_date, "progress")
        if existing_rel and not photo_replace_confirm:
            return (
                jsonify(
                    {
                        "ok": False,
                        "needs_confirm": True,
                        "log_date": log_date,
                        "existing_photo_url": photo_url_from_rel(existing_rel),
                        "message": "Ya existe una foto para esa fecha. Confirma para reemplazar.",
                    }
                ),
                409,
            )

        # Confirmado (o no existía): ahora sí guardamos el archivo
        try:
            saved_photo_rel = save_progress_photo(photo, log_date)
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception:
            return jsonify({"ok": False, "error": "No se pudo guardar la foto"}), 500
        photo_original_name = sanitize_filename(getattr(photo, "filename", "") or "")
        photo_yn = "Y"
    else:
        # Evita estados inconsistentes: no dejamos Y si no hay foto nueva ni existente.
        with _conn() as conn:
            existing_rel = get_existing_photo_rel(conn, log_date, "progress")
        if photo_yn == "Y" and not existing_rel:
            photo_yn = None

    try:
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO diet_log (
                  log_date, sleep_hours, sleep_quality, steps, weight_kg,
                  waist_cm, hip_cm, alcohol_units, creatine_yn, photo_yn
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    sleep_hours,
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

            old_photo_rel = ""
            if saved_photo_rel:
                # Si ya existía, lo capturamos ANTES de reemplazar para borrar luego
                old_photo_rel = get_existing_photo_rel(conn, log_date, "progress")

                conn.execute(
                    """
                    INSERT INTO photo_log (log_date, kind, path, original_name, created_at)
                    VALUES (?, 'progress', ?, ?, ?)
                    ON CONFLICT(log_date, kind) DO UPDATE SET
                      path=excluded.path,
                      original_name=excluded.original_name,
                      created_at=excluded.created_at;
                    """,
                    (
                        log_date,
                        saved_photo_rel,
                        photo_original_name or None,
                        datetime.now().replace(microsecond=0).isoformat(),
                    ),
                )

            conn.commit()

        # Borrado seguro fuera de la transacción, tras commit exitoso
        if saved_photo_rel and old_photo_rel and old_photo_rel != saved_photo_rel:
            safe_delete_uploaded_photo(old_photo_rel)

    except Exception as e:
        # Si falla DB, intentamos limpiar el nuevo archivo para no dejar basura
        if saved_photo_rel:
            safe_delete_uploaded_photo(saved_photo_rel)
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "log_date": log_date})


@APP.post("/api/diet/import/preview")
def api_diet_import_preview():
    file_storage = request.files.get("file")
    if not file_storage or not getattr(file_storage, "filename", ""):
        return jsonify({"ok": False, "error": "Debes subir un archivo CSV."}), 400

    filename = str(file_storage.filename or "").lower()
    if filename and not filename.endswith(".csv"):
        return jsonify({"ok": False, "error": "El archivo debe tener extension .csv."}), 400

    try:
        text = read_text_file_storage(file_storage)
        rows = parse_diet_import_csv(text)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo leer el CSV."}), 400

    with _conn() as conn:
        existing_dates = {
            r["log_date"] for r in conn.execute("SELECT log_date FROM diet_log;").fetchall()
        }

    out = classify_diet_import_rows(rows, existing_dates)
    return jsonify(
        {
            "ok": True,
            "summary": out["summary"],
            "preview": out["preview"],
            "accepted_columns": list(DIET_IMPORT_FIELDS),
        }
    )


@APP.post("/api/diet/import/apply")
def api_diet_import_apply():
    data = request.get_json(silent=True) or {}
    raw_rows = data.get("rows")
    if not isinstance(raw_rows, list) or not raw_rows:
        return jsonify({"ok": False, "error": "No hay filas para importar."}), 400

    prepared = []
    for idx, item in enumerate(raw_rows, start=1):
        if not isinstance(item, dict):
            return jsonify({"ok": False, "error": "Formato de filas invalido."}), 400
        line_no = safe_int(item.get("row_number")) or idx
        base_row = item.get("row") if isinstance(item.get("row"), dict) else item
        prepared.append((line_no, base_row))

    summary = {"total": len(prepared), "imported": 0, "conflict": 0, "invalid": 0}
    results = []
    seen_dates = set()

    with _conn() as conn:
        existing_dates = {
            r["log_date"] for r in conn.execute("SELECT log_date FROM diet_log;").fetchall()
        }

        for line_no, raw in prepared:
            normalized, errors, warnings = parse_diet_import_row(raw)
            log_date = normalized.get("log_date") or ""

            status = "imported"
            reasons = []

            if errors:
                status = "invalid"
                reasons.extend(errors)
            elif not log_date:
                status = "invalid"
                reasons.append("log_date faltante")
            elif log_date in seen_dates:
                status = "invalid"
                reasons.append("fecha duplicada dentro del bloque importado")
            elif log_date in existing_dates:
                status = "conflict"
                reasons.append("la fecha ya existe y no se sobrescribe")

            if status == "imported":
                try:
                    conn.execute(
                        """
                        INSERT INTO diet_log (
                          log_date, sleep_hours, sleep_quality, steps, weight_kg,
                          waist_cm, hip_cm, alcohol_units, creatine_yn, photo_yn
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            normalized["log_date"],
                            normalized["sleep_hours"],
                            normalized["sleep_quality"],
                            normalized["steps"],
                            normalized["weight_kg"],
                            normalized["waist_cm"],
                            normalized["hip_cm"],
                            normalized["alcohol_units"],
                            normalized["creatine_yn"],
                            normalized["photo_yn"],
                        ),
                    )

                    if normalized["photo_path"]:
                        conn.execute(
                            """
                            INSERT INTO photo_log (log_date, kind, path, original_name, created_at)
                            VALUES (?, 'progress', ?, ?, ?)
                            ON CONFLICT(log_date, kind) DO UPDATE SET
                              path=excluded.path,
                              original_name=excluded.original_name,
                              created_at=excluded.created_at;
                            """,
                            (
                                normalized["log_date"],
                                normalized["photo_path"],
                                sanitize_filename(os.path.basename(normalized["photo_path"])),
                                datetime.now().replace(microsecond=0).isoformat(),
                            ),
                        )

                    existing_dates.add(log_date)
                    summary["imported"] += 1
                except sqlite3.IntegrityError:
                    status = "conflict"
                    reasons.append("la fecha ya existe y no se sobrescribe")
                    summary["conflict"] += 1
                except Exception as e:
                    status = "invalid"
                    reasons.append(f"error DB: {str(e)}")
                    summary["invalid"] += 1
            elif status == "conflict":
                summary["conflict"] += 1
            else:
                summary["invalid"] += 1

            if log_date:
                seen_dates.add(log_date)
            if warnings:
                reasons.extend(warnings)

            results.append(
                {
                    "row_number": line_no,
                    "status": status,
                    "reason": "; ".join(reasons),
                    "row": normalized,
                }
            )

        conn.commit()

    return jsonify({"ok": True, "summary": summary, "results": results})


@APP.post("/api/workout")
def api_workout():
    data = request.get_json(silent=True) or {}

    log_date = (data.get("log_date") or "").strip()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date inválida"}), 400
    mode = entry_mode(data.get("entry_mode"))
    session_id = safe_int(data.get("session_id"))

    session_done_yn = yn_or_none(data.get("session_done_yn"))
    session_type = normalize_session_type(data.get("session_type"))
    class_done = (data.get("class_done") or data.get("class_activity") or "").strip() or None
    rpe_session = safe_int(data.get("rpe_session"))
    notes = (data.get("notes") or "").strip() or None
    exercises = parse_exercises_payload(data)
    if session_type == "clase":
        exercises = []

    try:
        with _conn() as conn:
            target_session_id = None
            created = False

            if mode == "edit":
                if session_id is None:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "Para editar un entreno debes indicar session_id.",
                            }
                        ),
                        400,
                    )
                exists = conn.execute(
                    "SELECT session_id FROM workout_session WHERE session_id = ? LIMIT 1;",
                    (session_id,),
                ).fetchone()
                if not exists:
                    return jsonify({"ok": False, "error": "Sesion no encontrada."}), 404
                target_session_id = session_id
            elif mode == "upsert":
                if session_id is not None:
                    exists = conn.execute(
                        "SELECT session_id FROM workout_session WHERE session_id = ? LIMIT 1;",
                        (session_id,),
                    ).fetchone()
                    if exists:
                        target_session_id = session_id
                if target_session_id is None:
                    existing_by_date = conn.execute(
                        """
                        SELECT session_id
                        FROM workout_session
                        WHERE log_date = ?
                        ORDER BY session_order ASC
                        LIMIT 1;
                        """,
                        (log_date,),
                    ).fetchone()
                    if existing_by_date:
                        target_session_id = existing_by_date["session_id"]

            if target_session_id is None:
                now_iso = datetime.now().replace(microsecond=0).isoformat()
                # Alta concurrente: recalcular session_order y reintentar si choca el UNIQUE(log_date, session_order).
                for _ in range(20):
                    next_order = conn.execute(
                        "SELECT COALESCE(MAX(session_order), 0) + 1 AS next_order FROM workout_session WHERE log_date = ?;",
                        (log_date,),
                    ).fetchone()["next_order"]
                    try:
                        cur = conn.execute(
                            """
                            INSERT INTO workout_session (
                              log_date, session_order, session_done_yn, session_type, class_done,
                              rpe_session, notes, created_at, updated_at
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
                                now_iso,
                                now_iso,
                            ),
                        )
                        target_session_id = cur.lastrowid
                        created = True
                        break
                    except sqlite3.IntegrityError:
                        continue
                if target_session_id is None:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "No se pudo crear la sesion por colision concurrente. Intenta de nuevo.",
                            }
                        ),
                        409,
                    )
            else:
                current = conn.execute(
                    """
                    SELECT log_date, session_order
                    FROM workout_session
                    WHERE session_id = ?;
                    """,
                    (target_session_id,),
                ).fetchone()
                next_order = current["session_order"] if current else 1
                if current and current["log_date"] != log_date:
                    next_order = conn.execute(
                        """
                        SELECT COALESCE(MAX(session_order), 0) + 1 AS next_order
                        FROM workout_session
                        WHERE log_date = ?;
                        """,
                        (log_date,),
                    ).fetchone()["next_order"]
                conn.execute(
                    """
                    UPDATE workout_session
                    SET
                      log_date = ?,
                      session_order = ?,
                      session_done_yn = ?,
                      session_type = ?,
                      class_done = ?,
                      rpe_session = ?,
                      notes = ?,
                      updated_at = ?
                    WHERE session_id = ?;
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
                        target_session_id,
                    ),
                )

            conn.execute(
                "DELETE FROM workout_exercise WHERE session_id = ?;",
                (target_session_id,),
            )
            for idx, ex in enumerate(exercises, start=1):
                conn.execute(
                    """
                    INSERT INTO workout_exercise (
                      session_id, exercise_name, set_order, weight_kg, reps, rpe, topset_text
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        target_session_id,
                        ex["exercise_name"],
                        idx,
                        ex["weight_kg"],
                        ex["reps"],
                        ex["rpe"],
                        ex["topset_text"],
                    ),
                )
            conn.commit()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify(
        {
            "ok": True,
            "log_date": log_date,
            "session_id": target_session_id,
            "entry_mode": "create" if created else "edit",
        }
    )


@APP.delete("/api/diet/<log_date>")
def api_diet_delete(log_date):
    log_date = (log_date or "").strip()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400

    with _conn() as conn:
        row = conn.execute(
            """
            SELECT d.log_date, p.path AS photo_path
            FROM diet_log d
            LEFT JOIN photo_log p
              ON p.log_date = d.log_date AND p.kind = 'progress'
            WHERE d.log_date = ?
            LIMIT 1;
            """,
            (log_date,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Registro de dieta no encontrado."}), 404

        photo_rel = row["photo_path"] or ""
        conn.execute("DELETE FROM photo_log WHERE log_date = ? AND kind = 'progress';", (log_date,))
        conn.execute("DELETE FROM diet_log WHERE log_date = ?;", (log_date,))
        conn.commit()

    if photo_rel:
        safe_delete_uploaded_photo(photo_rel)

    return jsonify({"ok": True, "log_date": log_date})


@APP.delete("/api/diet/<log_date>/photo")
def api_diet_photo_delete(log_date):
    log_date = (log_date or "").strip()
    if not valid_iso_date(log_date):
        return jsonify({"ok": False, "error": "log_date invalida"}), 400

    with _conn() as conn:
        row = conn.execute(
            """
            SELECT d.log_date, p.path AS photo_path
            FROM diet_log d
            LEFT JOIN photo_log p
              ON p.log_date = d.log_date AND p.kind = 'progress'
            WHERE d.log_date = ?
            LIMIT 1;
            """,
            (log_date,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Registro de check-in no encontrado."}), 404

        photo_rel = row["photo_path"] or ""
        conn.execute("UPDATE diet_log SET photo_yn = NULL WHERE log_date = ?;", (log_date,))
        if photo_rel:
            conn.execute("DELETE FROM photo_log WHERE log_date = ? AND kind = 'progress';", (log_date,))
        conn.commit()

    if photo_rel:
        safe_delete_uploaded_photo(photo_rel)

    return jsonify({"ok": True, "log_date": log_date, "photo_deleted": bool(photo_rel)})


@APP.delete("/api/workout/<int:session_id>")
def api_workout_delete(session_id: int):
    sid = int(session_id)
    with _conn() as conn:
        row = conn.execute(
            "SELECT session_id, log_date FROM workout_session WHERE session_id = ? LIMIT 1;",
            (sid,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Sesion de entreno no encontrada."}), 404

        conn.execute("DELETE FROM workout_session WHERE session_id = ?;", (sid,))
        conn.commit()

    return jsonify({"ok": True, "session_id": sid, "log_date": row["log_date"]})


# -----------------------------
# CSV templates
# -----------------------------
def _send_text_download(filename: str, text: str, mimetype: str):
    data = str(text or "").encode("utf-8")
    return send_file(
        BytesIO(data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


def _send_csv_download(filename: str, rows):
    buf = StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(list(row))
    csv_bytes = buf.getvalue().encode("utf-8")
    return send_file(
        BytesIO(csv_bytes),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=filename,
    )


@APP.get("/export/template/checkin-import.csv")
def export_checkin_import_template_csv():
    return _send_csv_download(
        "checkin_import_template.csv",
        [
            list(DIET_IMPORT_FIELDS),
            [
                "2026-03-01",
                "7.2",
                "8",
                "9500",
                "74.2",
                "82.3",
                "96.8",
                "0",
                "Y",
                "N",
                "",
            ],
        ],
    )


@APP.get("/export/template/plan-diet.csv")
def export_plan_diet_template_csv():
    return _send_csv_download(
        "plan_diet_template.csv",
        [
            list(PLAN_DIET_FIELDS),
            [
                "2026-03-01",
                "2200",
                "150",
                "220",
                "80",
                "Huevos + ensalada + arepa",
                "Fruta + yogur natural",
                "Pollo + legumbre + aguacate",
                "Queso + zanahoria",
                "Pescado + papa + verduras",
                "Plan de ejemplo",
            ],
        ],
    )


@APP.get("/export/template/plan-workout.csv")
def export_plan_workout_template_csv():
    if PLAN_WORKOUT_GUIDED_TEMPLATE_PATH.exists():
        guided_text = PLAN_WORKOUT_GUIDED_TEMPLATE_PATH.read_text(encoding="utf-8-sig")
        return _send_text_download(
            "plan_workout_template.csv",
            guided_text,
            "text/csv; charset=utf-8",
        )

    fields = list(PLAN_WORKOUT_COMBINED_FIELDS)

    def row_from(base: dict, exercises: list):
        row = {k: "" for k in fields}
        for key, value in (base or {}).items():
            if key in row:
                row[key] = value
        for idx, ex in enumerate(exercises or [], start=1):
            if idx > PLAN_WORKOUT_COMBINED_EXERCISE_SLOTS:
                break
            for suffix in PLAN_WORKOUT_COMBINED_EXERCISE_SUFFIXES:
                val = ex.get(suffix, "")
                row[f"exercise_{idx}_{suffix}"] = str(val) if val is not None else ""
        return [row[k] for k in fields]

    return _send_csv_download(
        "plan_workout_template.csv",
        [
            fields,
            row_from(
                {
                    "log_date": "2026-03-01",
                    "session_type": "pesas",
                    "warmup": "Bici 8 min + movilidad cadera",
                    "cardio": "Caminata 20 min",
                    "mobility_cooldown": "Estirar 10 min",
                    "additional_exercises": "Abducciones + gemelos",
                    "notes": "Pierna + gluteo · tecnica primero",
                },
                [
                    {
                        "name": "Hip Thrust",
                        "sets": "4",
                        "reps_min": "5",
                        "reps_max": "8",
                        "weight_kg": "120",
                        "rpe": "8",
                        "intensity_target": "RPE 7-8",
                        "progression_weight_rule": "+2.5kg al cerrar reps",
                        "progression_reps_rule": "+1 rep/serie antes de subir carga",
                    },
                    {
                        "name": "Sentadilla",
                        "sets": "4",
                        "reps_min": "5",
                        "reps_max": "8",
                        "weight_kg": "80",
                        "rpe": "7",
                        "intensity_target": "RPE 7",
                        "progression_weight_rule": "+2kg al cerrar reps",
                        "progression_reps_rule": "+1 rep/serie",
                    },
                ],
            ),
            row_from(
                {
                    "log_date": "2026-03-01",
                    "session_type": "clase",
                    "class_sessions": "Pilates 50 min",
                    "mobility_cooldown": "Movilidad suave",
                    "notes": "Clase tecnica + respiracion",
                },
                [],
            ),
            row_from(
                {
                    "log_date": "2026-03-01",
                    "session_type": "pesas",
                    "warmup": "Remo 6 min",
                    "mobility_cooldown": "Estirar 8 min",
                    "additional_exercises": "Band pull-aparts",
                    "notes": "Upper body PM",
                },
                [
                    {
                        "name": "Press banca",
                        "sets": "3",
                        "reps_min": "6",
                        "reps_max": "8",
                        "weight_kg": "60",
                        "rpe": "8",
                        "intensity_target": "RPE 8",
                        "progression_weight_rule": "+1.25kg",
                        "progression_reps_rule": "+1 rep",
                    }
                ],
            ),
        ],
    )


@APP.get("/export/template/plan-csv-ai-instructions.md")
def export_plan_csv_ai_instructions_md():
    source_path = PLAN_CSV_AI_SYSTEM_PROMPT_PATH
    download_name = "PLAN_CSV_AI_SYSTEM_PROMPT.md"
    if not source_path.exists():
        source_path = PLAN_CSV_AI_INSTRUCTIONS_LEGACY_PATH
        download_name = "PLAN_CSV_AI_INSTRUCTIONS.md"
    if not source_path.exists():
        return jsonify({"ok": False, "error": "No existe la guía de instrucciones IA."}), 404
    md_text = source_path.read_text(encoding="utf-8-sig")
    return _send_text_download(
        download_name,
        md_text,
        "text/markdown; charset=utf-8",
    )


@APP.get("/export/template/plan-csv-ai-system-prompt.md")
def export_plan_csv_ai_system_prompt_md():
    if not PLAN_CSV_AI_SYSTEM_PROMPT_PATH.exists():
        return jsonify({"ok": False, "error": "No existe el system prompt IA."}), 404
    md_text = PLAN_CSV_AI_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8-sig")
    return _send_text_download(
        "PLAN_CSV_AI_SYSTEM_PROMPT.md",
        md_text,
        "text/markdown; charset=utf-8",
    )


@APP.get("/export/template/plan-csv-ai-instructions-diet.md")
def export_plan_csv_ai_instructions_diet_md():
    if not PLAN_CSV_AI_INSTRUCTIONS_DIET_PATH.exists():
        return jsonify({"ok": False, "error": "No existe la guía IA de dieta."}), 404
    md_text = PLAN_CSV_AI_INSTRUCTIONS_DIET_PATH.read_text(encoding="utf-8-sig")
    return _send_text_download(
        "PLAN_CSV_AI_INSTRUCTIONS_DIET.md",
        md_text,
        "text/markdown; charset=utf-8",
    )


@APP.get("/export/template/plan-csv-ai-instructions-workout.md")
def export_plan_csv_ai_instructions_workout_md():
    if not PLAN_CSV_AI_INSTRUCTIONS_WORKOUT_PATH.exists():
        return jsonify({"ok": False, "error": "No existe la guía IA de entreno."}), 404
    md_text = PLAN_CSV_AI_INSTRUCTIONS_WORKOUT_PATH.read_text(encoding="utf-8-sig")
    return _send_text_download(
        "PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md",
        md_text,
        "text/markdown; charset=utf-8",
    )


@APP.get("/export/template/plan-workout-sessions.csv")
def export_plan_workout_sessions_template_csv():
    return _send_csv_download(
        "plan_workout_sessions_template.csv",
        [
            list(PLAN_WORKOUT_SESSION_FIELDS),
            [
                "2026-03-01",
                "A",
                "pesas",
                "Bici 8 min + movilidad cadera",
                "",
                "Caminata 20 min",
                "Estirar 10 min",
                "Abducciones + gemelos",
                "Sesion de ejemplo",
            ],
        ],
    )


@APP.get("/export/template/plan-workout-exercises.csv")
def export_plan_workout_exercises_template_csv():
    return _send_csv_download(
        "plan_workout_exercises_template.csv",
        [
            list(PLAN_WORKOUT_EXERCISE_FIELDS),
            [
                "2026-03-01",
                "A",
                "1",
                "Hip Thrust",
                "4",
                "5",
                "8",
                "120",
                "8",
                "RPE 7-8",
                "+2.5kg cuando completes reps max",
                "+1 rep por serie antes de subir peso",
            ],
        ],
    )


# -----------------------------
# CSV export
# -----------------------------
@APP.get("/export/check-ins.csv")
@APP.get("/export/diet.csv")
def export_checkins_csv():
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
              d.log_date, d.sleep_hours, d.sleep_quality, d.steps, d.weight_kg,
              d.waist_cm, d.hip_cm, d.alcohol_units, d.photo_yn,
              p.path AS photo_path
            FROM diet_log d
            LEFT JOIN photo_log p
              ON p.log_date = d.log_date AND p.kind = 'progress'
            ORDER BY d.log_date ASC;
            """
        ).fetchall()

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "log_date",
            "sleep_hours",
            "sleep_quality",
            "steps",
            "weight_kg",
            "waist_cm",
            "hip_cm",
            "whr",
            "alcohol_units",
            "photo_yn",
            "photo_path",
        ]
    )

    for r in rows:
        whr = ""
        try:
            if r["hip_cm"] and float(r["hip_cm"]) > 0:
                whr = float(r["waist_cm"] or 0) / float(r["hip_cm"])
        except Exception:
            whr = ""
        writer.writerow(
            [
                r["log_date"] or "",
                r["sleep_hours"] if r["sleep_hours"] is not None else "",
                r["sleep_quality"] if r["sleep_quality"] is not None else "",
                r["steps"] if r["steps"] is not None else "",
                r["weight_kg"] if r["weight_kg"] is not None else "",
                r["waist_cm"] if r["waist_cm"] is not None else "",
                r["hip_cm"] if r["hip_cm"] is not None else "",
                whr if whr != "" else "",
                r["alcohol_units"] if r["alcohol_units"] is not None else 0,
                r["photo_yn"] or "",
                r["photo_path"] or "",
            ]
        )

    csv_bytes = buf.getvalue().encode("utf-8")
    out_path = BASE_DIR / "check-ins.csv"
    out_path.write_bytes(csv_bytes)
    return send_file(out_path, as_attachment=True, download_name="check-ins.csv")


@APP.get("/export/workout.csv")
def export_workout_csv():
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
              s.log_date, s.session_id, s.session_order, s.session_type, s.session_done_yn,
              s.class_done, s.rpe_session, s.notes,
              e.set_order, e.exercise_name, e.weight_kg, e.reps, e.rpe
            FROM workout_session s
            LEFT JOIN workout_exercise e ON e.session_id = s.session_id
            ORDER BY s.log_date ASC, s.session_order ASC, e.set_order ASC, e.exercise_id ASC;
            """
        ).fetchall()

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "log_date",
            "session_id",
            "session_order",
            "session_type",
            "session_done_yn",
            "class_done",
            "rpe_session",
            "exercise_order",
            "exercise_name",
            "weight_kg",
            "reps",
            "rpe",
            "notes",
        ]
    )

    for r in rows:
        writer.writerow(
            [
                r["log_date"] or "",
                r["session_id"] if r["session_id"] is not None else "",
                r["session_order"] if r["session_order"] is not None else "",
                r["session_type"] or "clase",
                r["session_done_yn"] or "",
                r["class_done"] or "",
                r["rpe_session"] if r["rpe_session"] is not None else "",
                r["set_order"] if r["set_order"] is not None else "",
                r["exercise_name"] or "",
                r["weight_kg"] if r["weight_kg"] is not None else "",
                r["reps"] if r["reps"] is not None else "",
                r["rpe"] if r["rpe"] is not None else "",
                r["notes"] or "",
            ]
        )

    csv_bytes = buf.getvalue().encode("utf-8")
    out_path = BASE_DIR / "workout.csv"
    out_path.write_bytes(csv_bytes)
    return send_file(out_path, as_attachment=True, download_name="workout.csv")


@APP.get("/export/supplements.csv")
def export_supplements_csv():
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT
              c.supplement_id,
              c.name,
              c.doses_per_day,
              c.active_yn,
              c.notes AS catalog_notes,
              l.log_date,
              l.doses_taken,
              l.notes AS day_notes
            FROM supplement_catalog c
            LEFT JOIN supplement_daily_log l ON l.supplement_id = c.supplement_id
            ORDER BY c.name COLLATE NOCASE ASC, l.log_date ASC;
            """
        ).fetchall()

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "supplement_id",
            "name",
            "doses_per_day",
            "active_yn",
            "catalog_notes",
            "log_date",
            "doses_taken",
            "day_notes",
        ]
    )

    for r in rows:
        writer.writerow(
            [
                r["supplement_id"] if r["supplement_id"] is not None else "",
                r["name"] or "",
                r["doses_per_day"] if r["doses_per_day"] is not None else "",
                r["active_yn"] or "Y",
                r["catalog_notes"] or "",
                r["log_date"] or "",
                r["doses_taken"] if r["doses_taken"] is not None else "",
                r["day_notes"] or "",
            ]
        )

    csv_bytes = buf.getvalue().encode("utf-8")
    out_path = BASE_DIR / "supplements.csv"
    out_path.write_bytes(csv_bytes)
    return send_file(out_path, as_attachment=True, download_name="supplements.csv")


@APP.get("/backup/export")
def export_backup_zip():
    ensure_schema()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with TemporaryDirectory() as tmp:
        snapshot_db = Path(tmp) / "tracker.db"
        try:
            create_db_snapshot(snapshot_db)
        except Exception as e:
            return jsonify({"ok": False, "error": f"No se pudo crear snapshot DB: {str(e)}"}), 500

        mem = BytesIO()
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            meta = {
                "app": "tracker-local",
                "created_at": datetime.now().replace(microsecond=0).isoformat(),
                "version_hint": "v0.0.1.0",
                "db_file": "tracker.db",
                "upload_root": "uploads/",
            }
            zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
            zf.write(snapshot_db, arcname="tracker.db")

            uploads_root = Path(UPLOAD_ROOT)
            if uploads_root.exists():
                for p in sorted(uploads_root.rglob("*")):
                    if not p.is_file():
                        continue
                    rel = p.relative_to(uploads_root).as_posix()
                    zf.write(p, arcname=f"uploads/{rel}")

        mem.seek(0)
        return send_file(
            mem,
            as_attachment=True,
            mimetype="application/zip",
            download_name=f"tracker-backup-{stamp}.zip",
        )


@APP.post("/backup/restore")
def restore_backup_zip():
    file_storage = request.files.get("backup_file")
    if not file_storage or not getattr(file_storage, "filename", ""):
        return jsonify({"ok": False, "error": "Debes seleccionar un archivo .zip de backup."}), 400

    if not truthy(request.form.get("restore_confirm")):
        return (
            jsonify(
                {
                    "ok": False,
                    "needs_confirm": True,
                    "error": "Confirma restauracion para continuar.",
                }
            ),
            409,
        )

    try:
        raw = file_storage.read() or b""
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo leer el archivo de backup."}), 400
    if not raw:
        return jsonify({"ok": False, "error": "Backup vacio."}), 400

    try:
        zip_obj = zipfile.ZipFile(BytesIO(raw))
    except Exception:
        return jsonify({"ok": False, "error": "Archivo ZIP invalido."}), 400

    names = zip_obj.namelist()
    if not names:
        return jsonify({"ok": False, "error": "El ZIP no contiene archivos."}), 400
    if any(not is_safe_backup_member(n) for n in names if n and not n.endswith("/")):
        return jsonify({"ok": False, "error": "ZIP invalido (rutas inseguras)."}), 400

    db_candidates = [n for n in names if Path(n).name == "tracker.db"]
    if not db_candidates:
        return jsonify({"ok": False, "error": "El backup no contiene tracker.db."}), 400
    db_member = db_candidates[0]

    with TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        staged_db = tmp_root / "staged_tracker.db"
        staged_uploads = tmp_root / "staged_uploads"
        rollback_db = tmp_root / "rollback_tracker.db"
        rollback_uploads = tmp_root / "rollback_uploads"

        try:
            staged_db.write_bytes(zip_obj.read(db_member))
        except Exception:
            return jsonify({"ok": False, "error": "No se pudo extraer tracker.db del backup."}), 400

        # Validacion basica de SQLite
        try:
            with closing(sqlite3.connect(staged_db)) as conn:
                conn.execute("PRAGMA schema_version;").fetchone()
        except Exception:
            return jsonify({"ok": False, "error": "tracker.db en backup no es una DB valida."}), 400

        restored_upload_files = 0
        for name in names:
            if not name.startswith("uploads/"):
                continue
            if name.endswith("/"):
                continue
            rel = name[len("uploads/") :]
            if not rel:
                continue
            dest = staged_uploads / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                dest.write_bytes(zip_obj.read(name))
            except Exception:
                return jsonify({"ok": False, "error": "No se pudo extraer uploads del backup."}), 400
            restored_upload_files += 1

        zip_obj.close()

        upload_root_path = Path(UPLOAD_ROOT)
        try:
            if DB_PATH.exists():
                rollback_db.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(DB_PATH, rollback_db)
            if upload_root_path.exists():
                shutil.copytree(upload_root_path, rollback_uploads)
        except Exception as e:
            return jsonify({"ok": False, "error": f"No se pudo preparar rollback: {str(e)}"}), 500

        try:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_db, DB_PATH)

            if upload_root_path.exists():
                shutil.rmtree(upload_root_path)
            if staged_uploads.exists():
                shutil.copytree(staged_uploads, upload_root_path)
            else:
                upload_root_path.mkdir(parents=True, exist_ok=True)

            ensure_schema()
        except Exception as e:
            # Rollback best effort
            try:
                if rollback_db.exists():
                    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(rollback_db, DB_PATH)
                if upload_root_path.exists():
                    shutil.rmtree(upload_root_path)
                if rollback_uploads.exists():
                    shutil.copytree(rollback_uploads, upload_root_path)
            except Exception:
                pass
            return jsonify({"ok": False, "error": f"Fallo al restaurar backup: {str(e)}"}), 500

    with _conn() as conn:
        diet_count = conn.execute("SELECT COUNT(*) AS n FROM diet_log;").fetchone()["n"]
        if table_exists(conn, "workout_session"):
            workout_count = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_session;"
            ).fetchone()["n"]
        else:
            workout_count = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_log;"
            ).fetchone()["n"]

    return jsonify(
        {
            "ok": True,
            "summary": {
                "diet_rows": diet_count,
                "workout_rows": workout_count,
                "upload_files": restored_upload_files,
            },
        }
    )


# -----------------------------
# Static for uploads (opcional; normalmente Flask sirve /static/*)
# -----------------------------
@APP.get("/static/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOAD_ROOT, filename)


@APP.get("/uploads/<path:filename>")
def serve_uploads_legacy(filename):
    return send_from_directory(UPLOAD_ROOT, filename)


if __name__ == "__main__":
    host = os.environ.get("TRACKER_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("TRACKER_PORT", "5050"))
    except Exception:
        port = 5050
    APP.run(host=host, port=port, debug=False, use_reloader=False)
