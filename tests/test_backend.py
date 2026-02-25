import csv
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import contextmanager
from pathlib import Path

import app as tracker
from werkzeug.datastructures import FileStorage


class TrackerBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

        self.orig_db_path = tracker.DB_PATH
        self.orig_upload_root = tracker.UPLOAD_ROOT
        self.orig_max_len = tracker.APP.config.get("MAX_CONTENT_LENGTH")
        self.orig_testing = tracker.APP.config.get("TESTING")
        self.orig_auth_enabled = tracker.AUTH_ENABLED
        self.orig_auth_hash = tracker.AUTH_PASSWORD_HASH
        self.orig_photo_compression_enabled = tracker.PHOTO_COMPRESSION_ENABLED
        self.orig_photo_max_side = tracker.PHOTO_MAX_SIDE
        self.orig_photo_quality = tracker.PHOTO_QUALITY
        self.orig_photo_prefer_webp = tracker.PHOTO_PREFER_WEBP

        tracker.DB_PATH = self.tmp_path / "tracker_test.db"
        tracker.UPLOAD_ROOT = str(self.tmp_path / "uploads")
        tracker.ensure_schema()

        tracker.APP.config["TESTING"] = True
        tracker.APP.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
        self._client_ctx = tracker.APP.test_client()
        self.client = self._client_ctx.__enter__()

    def tearDown(self):
        tracker.DB_PATH = self.orig_db_path
        tracker.UPLOAD_ROOT = self.orig_upload_root
        tracker.APP.config["MAX_CONTENT_LENGTH"] = self.orig_max_len
        tracker.APP.config["TESTING"] = self.orig_testing
        tracker.AUTH_ENABLED = self.orig_auth_enabled
        tracker.AUTH_PASSWORD_HASH = self.orig_auth_hash
        tracker.PHOTO_COMPRESSION_ENABLED = self.orig_photo_compression_enabled
        tracker.PHOTO_MAX_SIDE = self.orig_photo_max_side
        tracker.PHOTO_QUALITY = self.orig_photo_quality
        tracker.PHOTO_PREFER_WEBP = self.orig_photo_prefer_webp
        if getattr(self, "_client_ctx", None) is not None:
            self._client_ctx.__exit__(None, None, None)
        self.tmp.cleanup()

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(tracker.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def test_helper_functions(self):
        self.assertTrue(tracker.valid_iso_date("2026-02-15"))
        self.assertFalse(tracker.valid_iso_date("15-02-2026"))
        self.assertEqual(tracker.safe_int("12"), 12)
        self.assertIsNone(tracker.safe_int("x"))
        self.assertEqual(tracker.safe_float("7.5"), 7.5)
        self.assertIsNone(tracker.safe_float("bad"))
        self.assertEqual(tracker.yn_or_none("y"), "Y")
        self.assertEqual(tracker.yn_or_none("N"), "N")
        self.assertIsNone(tracker.yn_or_none("maybe"))
        self.assertTrue(tracker.truthy("yes"))
        self.assertFalse(tracker.truthy("no"))
        self.assertEqual(
            tracker.photo_url_from_rel("static/uploads/2026-02-15/a.jpg"),
            "/uploads/2026-02-15/a.jpg",
        )
        self.assertEqual(
            tracker.photo_url_from_rel("uploads/2026-02-15/a.jpg"),
            "/uploads/2026-02-15/a.jpg",
        )

    def test_pages_and_state(self):
        for path in ["/", "/help", "/changelog"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, path)

        res = self.client.get("/api/state?limit=1")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertIn("summary", payload)
        self.assertIn("diet", payload)
        self.assertIn("workout", payload)
        self.assertIn("photos", payload)
        self.assertIn("plan_today", payload)
        self.assertIsInstance(payload["diet"], list)
        self.assertIsInstance(payload["workout"], list)
        self.assertIsInstance(payload["photos"], list)
        self.assertIsInstance(payload["plan_today"], dict)

    def test_local_auth_password_flow(self):
        tracker.AUTH_ENABLED = True
        tracker.AUTH_PASSWORD_HASH = tracker.generate_password_hash("clave-secreta")
        tracker.APP.config["TESTING"] = False
        client = tracker.APP.test_client()

        res = client.get("/", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

        bad = client.post(
            "/login",
            data={"password": "incorrecta", "next": "/"},
            follow_redirects=False,
        )
        self.assertEqual(bad.status_code, 401)

        ok = client.post(
            "/login",
            data={"password": "clave-secreta", "next": "/"},
            follow_redirects=False,
        )
        self.assertEqual(ok.status_code, 302)
        self.assertEqual(ok.headers.get("Location"), "/")

        state_ok = client.get("/api/state?limit=1")
        self.assertEqual(state_ok.status_code, 200)

        logout = client.post("/logout")
        self.assertEqual(logout.status_code, 200)

        state_blocked = client.get("/api/state?limit=1")
        self.assertEqual(state_blocked.status_code, 401)

    def test_state_supports_summary_range_and_trend(self):
        rows = [
            ("2026-04-01", 7.0, 10000, 70.0, 80.0, 100.0),
            ("2026-04-10", 8.0, 11000, 69.0, 78.0, 100.0),
            ("2026-04-20", 6.0, 9000, 68.5, 76.0, 100.0),
        ]
        for log_date, sleep, steps, weight, waist, hip in rows:
            res = self.client.post(
                "/api/diet",
                json={
                    "log_date": log_date,
                    "sleep_hours": sleep,
                    "steps": steps,
                    "weight_kg": weight,
                    "waist_cm": waist,
                    "hip_cm": hip,
                },
            )
            self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

        payload = self.client.get(
            "/api/state?limit=14&date_from=2026-04-01&date_to=2026-04-20"
        ).get_json()
        summary = payload["summary"]
        self.assertEqual(summary["mode"], "range")
        self.assertEqual(summary["date_from"], "2026-04-01")
        self.assertEqual(summary["date_to"], "2026-04-20")
        self.assertAlmostEqual(summary["avg_sleep"], 7.0, places=6)
        self.assertAlmostEqual(summary["avg_steps"], 10000.0, places=6)
        self.assertAlmostEqual(summary["avg_weight"], (70.0 + 69.0 + 68.5) / 3.0, places=6)
        self.assertAlmostEqual(summary["avg_whr"], (0.8 + 0.78 + 0.76) / 3.0, places=6)
        self.assertAlmostEqual(summary["trend"]["delta_weight"], -1.5, places=6)
        self.assertAlmostEqual(summary["trend"]["delta_whr"], -0.04, places=6)
        self.assertRegex(summary["trend"]["text"].lower(), r"reduccion|buena señal|bajan")
        self.assertEqual(summary["series"]["count"], 3)
        self.assertEqual(len(summary["series"]["points"]), 3)

    def test_invalid_summary_range_falls_back_to_rolling_mode(self):
        self.client.post(
            "/api/diet",
            json={"log_date": "2026-05-01", "sleep_hours": 7.0, "steps": 9000},
        )
        payload = self.client.get(
            "/api/state?limit=14&date_from=2026-05-05&date_to=2026-05-01"
        ).get_json()
        self.assertEqual(payload["summary"]["mode"], "rolling_7d")
        self.assertTrue(tracker.valid_iso_date(payload["summary"]["date_from"]))
        self.assertTrue(tracker.valid_iso_date(payload["summary"]["date_to"]))

    def test_summary_window_90_days_with_seed_over_120_days(self):
        today = tracker.datetime.now().date()
        with self._db() as conn:
            for offset in range(119, -1, -1):
                log_date = (today - tracker.timedelta(days=offset)).isoformat()
                conn.execute(
                    """
                    INSERT INTO diet_log (
                      log_date, sleep_hours, sleep_quality, steps, weight_kg,
                      waist_cm, hip_cm, alcohol_units, creatine_yn, photo_yn
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL);
                    """,
                    (
                        log_date,
                        7.0,
                        8,
                        9000 + (offset % 50),
                        70.0 + (offset * 0.01),
                        80.0,
                        100.0,
                    ),
                )
            conn.commit()

        payload = self.client.get("/api/state?limit=15&summary_days=90").get_json()
        summary = payload["summary"]
        self.assertEqual(summary["mode"], "rolling_90d")
        self.assertEqual(summary["window_days"], 90)
        self.assertEqual(summary["coverage"]["current_target"], 90)
        self.assertEqual(summary["coverage"]["current_count"], 90)
        self.assertEqual(summary["series"]["count"], 90)

    def test_diet_upsert_and_limit_fallback(self):
        today = tracker.datetime.now().date()
        dates = [
            (today - tracker.timedelta(days=offset)).isoformat()
            for offset in range(19, -1, -1)
        ]
        for idx, date in enumerate(dates, start=1):
            res = self.client.post(
                "/api/diet",
                json={
                    "log_date": date,
                    "sleep_hours": 7.0,
                    "steps": 8000 + idx,
                    "weight_kg": 70.0 + idx / 10.0,
                    "waist_cm": 80.0,
                    "hip_cm": 100.0,
                },
            )
            self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

        # limit inválido -> fallback 15
        state = self.client.get("/api/state?limit=abc").get_json()
        self.assertEqual(len(state["diet"]), 15)

        # upsert de misma fecha no duplica
        latest_date = dates[-1]
        res = self.client.post(
            "/api/diet",
            json={
                "log_date": latest_date,
                "sleep_hours": 8.4,
                "steps": 12345,
            },
        )
        self.assertEqual(res.status_code, 200)

        with self._db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM diet_log WHERE log_date = ?;",
                (latest_date,),
            ).fetchone()["n"]
            row = conn.execute(
                "SELECT steps, sleep_hours FROM diet_log WHERE log_date = ?;",
                (latest_date,),
            ).fetchone()

        self.assertEqual(count, 1)
        self.assertEqual(row["steps"], 12345)
        self.assertAlmostEqual(row["sleep_hours"], 8.4)

    def test_limit_windows_use_calendar_days(self):
        today = tracker.datetime.now().date()
        d1 = (today - tracker.timedelta(days=20)).isoformat()
        d2 = (today - tracker.timedelta(days=10)).isoformat()
        d3 = today.isoformat()

        for day in (d1, d2, d3):
            res = self.client.post(
                "/api/diet",
                json={
                    "log_date": day,
                    "sleep_hours": 7.0,
                    "steps": 9000,
                    "weight_kg": 70.0,
                    "waist_cm": 80.0,
                    "hip_cm": 100.0,
                },
            )
            self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

        for idx, day in enumerate((d1, d2, d3), start=1):
            res = self.client.post(
                "/api/workout",
                json={
                    "entry_mode": "create",
                    "log_date": day,
                    "session_type": "clase",
                    "session_done_yn": "Y",
                    "class_done": f"Clase {idx}",
                },
            )
            self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

        state_7 = self.client.get("/api/state?limit=7").get_json()
        diet_7 = [r["log_date"] for r in state_7.get("diet", [])]
        workout_7 = [r["log_date"] for r in state_7.get("workout", [])]
        self.assertEqual(diet_7, [d3])
        self.assertEqual(workout_7, [d3])

        state_15 = self.client.get("/api/state?limit=15").get_json()
        diet_15 = [r["log_date"] for r in state_15.get("diet", [])]
        workout_15 = [r["log_date"] for r in state_15.get("workout", [])]
        self.assertEqual(diet_15, [d3, d2])
        self.assertEqual(workout_15, [d3, d2])

    def test_workout_upsert_and_export_csv_escaping(self):
        payload = {
            "log_date": "2026-02-10",
            "session_type": "pesas",
            "session_done_yn": "Y",
            "class_done": "PULL, HEAVY",
            "rpe_session": 8,
            "exercises_json": json.dumps(
                [
                    {"exercise_name": "Hip Thrust", "weight_kg": 120, "reps": 6, "rpe": 8},
                    {"exercise_name": "Sentadilla", "weight_kg": 80, "reps": 8, "rpe": 7},
                ]
            ),
            "notes": 'Notas con coma, comillas "dobles" y texto',
        }
        res = self.client.post("/api/workout", json=payload)
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

        # upsert fecha existente
        payload["notes"] = "Notas actualizadas, sigue con coma"
        res = self.client.post("/api/workout", json=payload)
        self.assertEqual(res.status_code, 200)

        with self._db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_session WHERE log_date = ?;",
                ("2026-02-10",),
            ).fetchone()["n"]
        self.assertEqual(count, 1)

        exp = self.client.get("/export/workout.csv")
        self.assertEqual(exp.status_code, 200)
        text = exp.get_data(as_text=True)
        exp.close()
        rows = list(csv.reader(io.StringIO(text)))

        self.assertEqual(rows[0][0], "log_date")
        headers = rows[0]
        session_id_idx = headers.index("session_id")
        session_order_idx = headers.index("session_order")
        type_idx = headers.index("session_type")
        class_idx = headers.index("class_done")
        notes_idx = headers.index("notes")
        ex_name_idx = headers.index("exercise_name")
        weight_idx = headers.index("weight_kg")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][0], "2026-02-10")
        self.assertNotEqual(rows[1][session_id_idx], "")
        self.assertEqual(rows[1][session_order_idx], "1")
        self.assertEqual(rows[1][type_idx], "pesas")
        self.assertEqual(rows[1][class_idx], "PULL, HEAVY")
        self.assertEqual(rows[1][notes_idx], "Notas actualizadas, sigue con coma")
        self.assertEqual(rows[1][ex_name_idx], "Hip Thrust")
        self.assertEqual(rows[1][weight_idx], "120.0")

    def test_create_mode_blocks_existing_day_and_edit_mode_allows_update(self):
        base = {
            "log_date": "2026-02-21",
            "sleep_hours": 7.0,
            "steps": 9000,
        }
        first = self.client.post("/api/diet", json=base)
        self.assertEqual(first.status_code, 200)

        blocked = self.client.post(
            "/api/diet",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-21",
                "sleep_hours": 8.2,
                "steps": 11111,
            },
        )
        self.assertEqual(blocked.status_code, 409)
        payload = blocked.get_json()
        self.assertTrue(payload.get("needs_edit"))

        with self._db() as conn:
            row = conn.execute(
                "SELECT sleep_hours, steps FROM diet_log WHERE log_date = ?;",
                ("2026-02-21",),
            ).fetchone()
        self.assertAlmostEqual(row["sleep_hours"], 7.0)
        self.assertEqual(row["steps"], 9000)

        updated = self.client.post(
            "/api/diet",
            json={
                "entry_mode": "edit",
                "log_date": "2026-02-21",
                "sleep_hours": 8.2,
                "steps": 11111,
            },
        )
        self.assertEqual(updated.status_code, 200)

        with self._db() as conn:
            row2 = conn.execute(
                "SELECT sleep_hours, steps FROM diet_log WHERE log_date = ?;",
                ("2026-02-21",),
            ).fetchone()
        self.assertAlmostEqual(row2["sleep_hours"], 8.2)
        self.assertEqual(row2["steps"], 11111)

    def test_workout_create_mode_allows_multiple_sessions_same_day_and_edit_mode_updates_target(self):
        first = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-22",
                "session_done_yn": "Y",
                "class_done": "PILATES",
            },
        )
        self.assertEqual(first.status_code, 200)
        first_session_id = first.get_json()["session_id"]

        second = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-22",
                "session_done_yn": "N",
                "class_done": "FUERZA PM",
            },
        )
        self.assertEqual(second.status_code, 200)
        second_session_id = second.get_json()["session_id"]
        self.assertNotEqual(first_session_id, second_session_id)

        with self._db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_session WHERE log_date = ?;",
                ("2026-02-22",),
            ).fetchone()["n"]
            rows = conn.execute(
                """
                SELECT session_order, session_done_yn, class_done
                FROM workout_session
                WHERE log_date = ?
                ORDER BY session_order ASC;
                """,
                ("2026-02-22",),
            ).fetchone()
        self.assertEqual(count, 2)
        self.assertEqual(rows["class_done"], "PILATES")

        updated = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "edit",
                "session_id": first_session_id,
                "log_date": "2026-02-22",
                "session_done_yn": "N",
                "class_done": "CARDIO",
            },
        )
        self.assertEqual(updated.status_code, 200)

        with self._db() as conn:
            first_row = conn.execute(
                "SELECT session_done_yn, class_done FROM workout_session WHERE session_id = ?;",
                (first_session_id,),
            ).fetchone()
            second_row = conn.execute(
                "SELECT session_done_yn, class_done FROM workout_session WHERE session_id = ?;",
                (second_session_id,),
            ).fetchone()
        self.assertEqual(first_row["session_done_yn"], "N")
        self.assertEqual(first_row["class_done"], "CARDIO")
        self.assertEqual(second_row["session_done_yn"], "N")
        self.assertEqual(second_row["class_done"], "FUERZA PM")

    def test_workout_edit_allows_clearing_session_done_state_to_null(self):
        created = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-24",
                "session_type": "clase",
                "session_done_yn": "Y",
                "class_done": "CLASE BASE",
            },
        )
        self.assertEqual(created.status_code, 200, created.get_data(as_text=True))
        session_id = created.get_json()["session_id"]

        cleared = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "edit",
                "session_id": session_id,
                "log_date": "2026-02-24",
                "session_type": "clase",
                "session_done_yn": "",
                "class_done": "CLASE BASE",
            },
        )
        self.assertEqual(cleared.status_code, 200, cleared.get_data(as_text=True))

        with self._db() as conn:
            row = conn.execute(
                "SELECT session_done_yn FROM workout_session WHERE session_id = ?;",
                (session_id,),
            ).fetchone()
        self.assertIsNone(row["session_done_yn"])

    def test_workout_structured_fields_and_deltas(self):
        first = self.client.post(
            "/api/workout",
            json={
                "log_date": "2026-02-23",
                "session_type": "pesas",
                "session_done_yn": "Y",
                "exercises_json": json.dumps(
                    [
                        {
                            "exercise_name": "Hip Thrust",
                            "weight_kg": 100,
                            "reps": 6,
                            "rpe": 7.5,
                        }
                    ]
                ),
            },
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/workout",
            json={
                "log_date": "2026-02-24",
                "session_type": "pesas",
                "session_done_yn": "Y",
                "exercises_json": json.dumps(
                    [
                        {
                            "exercise_name": "Hip Thrust",
                            "weight_kg": 105,
                            "reps": 7,
                            "rpe": 8,
                        }
                    ]
                ),
            },
        )
        self.assertEqual(second.status_code, 200)

        state = self.client.get("/api/state?limit=14").get_json()
        row = next((r for r in state["workout"] if r["log_date"] == "2026-02-24"), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["session_type"], "pesas")
        self.assertEqual(len(row["exercises"]), 1)
        ex = row["exercises"][0]
        self.assertEqual(ex["exercise_name"], "Hip Thrust")
        self.assertAlmostEqual(ex["weight_kg"], 105.0)
        self.assertEqual(ex["reps"], 7)
        self.assertAlmostEqual(ex["delta_weight"], 5.0)
        self.assertEqual(ex["delta_reps"], 1)

    def test_workout_strength_create_with_empty_exercises_persists_zero(self):
        created = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-24",
                "session_type": "pesas",
                "session_done_yn": "Y",
                "exercises_json": "[]",
            },
        )
        self.assertEqual(created.status_code, 200, created.get_data(as_text=True))
        session_id = created.get_json()["session_id"]

        with self._db() as conn:
            ex_count = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_exercise WHERE session_id = ?;",
                (session_id,),
            ).fetchone()["n"]
        self.assertEqual(ex_count, 0)

        state = self.client.get("/api/state?limit=7").get_json()
        row = next((r for r in state.get("workout", []) if r.get("session_id") == session_id), None)
        self.assertIsNotNone(row)
        self.assertEqual(row.get("session_type"), "pesas")
        self.assertEqual(len(row.get("exercises") or []), 0)

    def test_delete_diet_removes_row_photo_and_file(self):
        created = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-25",
                "sleep_hours": "7.1",
                "photo": (io.BytesIO(b"img-bytes"), "photo.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(created.status_code, 200, created.get_data(as_text=True))

        with self._db() as conn:
            photo_rel = conn.execute(
                "SELECT path FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-02-25",),
            ).fetchone()["path"]
        photo_abs = tracker.photo_rel_to_abs(photo_rel)
        self.assertTrue(photo_abs and Path(photo_abs).exists())

        deleted = self.client.delete("/api/diet/2026-02-25")
        self.assertEqual(deleted.status_code, 200, deleted.get_data(as_text=True))
        payload = deleted.get_json()
        self.assertTrue(payload.get("ok"))

        with self._db() as conn:
            diet_row = conn.execute(
                "SELECT 1 FROM diet_log WHERE log_date = ?;",
                ("2026-02-25",),
            ).fetchone()
            photo_row = conn.execute(
                "SELECT 1 FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-02-25",),
            ).fetchone()
        self.assertIsNone(diet_row)
        self.assertIsNone(photo_row)
        self.assertFalse(Path(photo_abs).exists())

    def test_delete_diet_photo_only_keeps_checkin(self):
        created = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-25",
                "sleep_hours": "7.2",
                "steps": "9300",
                "photo": (io.BytesIO(b"img-bytes"), "photo.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(created.status_code, 200, created.get_data(as_text=True))

        with self._db() as conn:
            photo_rel = conn.execute(
                "SELECT path FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-02-25",),
            ).fetchone()["path"]
        photo_abs = tracker.photo_rel_to_abs(photo_rel)
        self.assertTrue(photo_abs and Path(photo_abs).exists())

        deleted = self.client.delete("/api/diet/2026-02-25/photo")
        self.assertEqual(deleted.status_code, 200, deleted.get_data(as_text=True))
        payload = deleted.get_json()
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("photo_deleted"))

        with self._db() as conn:
            diet_row = conn.execute(
                "SELECT sleep_hours, steps, photo_yn FROM diet_log WHERE log_date = ?;",
                ("2026-02-25",),
            ).fetchone()
            photo_row = conn.execute(
                "SELECT 1 FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-02-25",),
            ).fetchone()
        self.assertIsNotNone(diet_row)
        self.assertAlmostEqual(diet_row["sleep_hours"], 7.2)
        self.assertEqual(diet_row["steps"], 9300)
        self.assertIsNone(diet_row["photo_yn"])
        self.assertIsNone(photo_row)
        self.assertFalse(Path(photo_abs).exists())

        state = self.client.get("/api/state?limit=7").get_json()
        row = next((r for r in state["diet"] if r["log_date"] == "2026-02-25"), None)
        self.assertIsNotNone(row)
        self.assertEqual(row.get("photo_url", ""), "")

    def test_delete_workout_removes_single_session_and_children(self):
        first = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-26",
                "session_type": "pesas",
                "session_done_yn": "Y",
                "exercises_json": json.dumps(
                    [{"exercise_name": "Hip Thrust", "weight_kg": 110, "reps": 6, "rpe": 8}]
                ),
            },
        )
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))
        first_id = int(first.get_json()["session_id"])

        second = self.client.post(
            "/api/workout",
            json={
                "entry_mode": "create",
                "log_date": "2026-02-26",
                "session_type": "clase",
                "session_done_yn": "N",
                "class_done": "PILATES",
            },
        )
        self.assertEqual(second.status_code, 200, second.get_data(as_text=True))
        second_id = int(second.get_json()["session_id"])
        self.assertNotEqual(first_id, second_id)

        deleted = self.client.delete(f"/api/workout/{first_id}")
        self.assertEqual(deleted.status_code, 200, deleted.get_data(as_text=True))
        payload = deleted.get_json()
        self.assertTrue(payload.get("ok"))

        with self._db() as conn:
            first_row = conn.execute(
                "SELECT 1 FROM workout_session WHERE session_id = ?;",
                (first_id,),
            ).fetchone()
            second_row = conn.execute(
                "SELECT 1 FROM workout_session WHERE session_id = ?;",
                (second_id,),
            ).fetchone()
            children = conn.execute(
                "SELECT COUNT(*) AS n FROM workout_exercise WHERE session_id = ?;",
                (first_id,),
            ).fetchone()["n"]
        self.assertIsNone(first_row)
        self.assertIsNotNone(second_row)
        self.assertEqual(children, 0)

    def test_diet_export_includes_whr(self):
        res = self.client.post(
            "/api/diet",
            json={
                "log_date": "2026-02-11",
                "waist_cm": 75.0,
                "hip_cm": 100.0,
                "alcohol_units": 0,
                "creatine_yn": "Y",
            },
        )
        self.assertEqual(res.status_code, 200)

        exp = self.client.get("/export/diet.csv")
        self.assertEqual(exp.status_code, 200)
        text = exp.get_data(as_text=True)
        exp.close()
        rows = list(csv.reader(io.StringIO(text)))

        self.assertIn("whr", rows[0])
        whr_idx = rows[0].index("whr")
        self.assertEqual(rows[1][0], "2026-02-11")
        self.assertAlmostEqual(float(rows[1][whr_idx]), 0.75, places=6)

    def test_diet_import_preview_classifies_valid_conflict_and_invalid_rows(self):
        self.client.post(
            "/api/diet",
            json={
                "log_date": "2026-03-01",
                "sleep_hours": 7.0,
                "steps": 8000,
            },
        )

        csv_text = """log_date,sleep_hours,steps,weight_kg,waist_cm,hip_cm,creatine_yn,alcohol_units
2026-03-01,7.1,9000,70.0,78.0,98.0,Y,0
2026-03-02,7.4,9500,70.2,78.2,97.5,N,1
bad-date,7,9000,70,78,97,Y,0
2026-03-02,7.0,9200,70.1,78,97,Y,0
"""
        res = self.client.post(
            "/api/diet/import/preview",
            data={"file": (io.BytesIO(csv_text.encode("utf-8")), "diet.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        payload = res.get_json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["summary"]["total"], 4)
        self.assertEqual(payload["summary"]["valid"], 1)
        self.assertEqual(payload["summary"]["conflict"], 1)
        self.assertEqual(payload["summary"]["invalid"], 2)

        by_line = {item["row_number"]: item for item in payload.get("preview", [])}
        self.assertEqual(by_line[2]["status"], "conflict")
        self.assertEqual(by_line[3]["status"], "valid")
        self.assertEqual(by_line[4]["status"], "invalid")
        self.assertEqual(by_line[5]["status"], "invalid")

    def test_diet_import_apply_imports_new_rows_and_skips_conflicts(self):
        self.client.post(
            "/api/diet",
            json={
                "log_date": "2026-03-10",
                "sleep_hours": 7.0,
                "steps": 8000,
            },
        )

        res = self.client.post(
            "/api/diet/import/apply",
            json={
                "rows": [
                    {
                        "row_number": 2,
                        "row": {
                            "log_date": "2026-03-10",
                            "sleep_hours": "8.1",
                            "steps": "11111",
                        },
                    },
                    {
                        "row_number": 3,
                        "row": {
                            "log_date": "2026-03-11",
                            "sleep_hours": "7.3",
                            "steps": "9100",
                            "weight_kg": "69.8",
                            "waist_cm": "77.0",
                            "hip_cm": "96.0",
                            "creatine_yn": "Y",
                            "photo_yn": "Y",
                            "photo_path": "uploads/2026-03-11/progress.png",
                        },
                    },
                    {
                        "row_number": 4,
                        "row": {
                            "log_date": "mal-fecha",
                            "steps": "x",
                        },
                    },
                ]
            },
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        payload = res.get_json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["summary"]["total"], 3)
        self.assertEqual(payload["summary"]["imported"], 1)
        self.assertEqual(payload["summary"]["conflict"], 1)
        self.assertEqual(payload["summary"]["invalid"], 1)

        with self._db() as conn:
            existing = conn.execute(
                "SELECT sleep_hours, steps FROM diet_log WHERE log_date = ?;",
                ("2026-03-10",),
            ).fetchone()
            imported = conn.execute(
                "SELECT sleep_hours, steps, weight_kg, photo_yn FROM diet_log WHERE log_date = ?;",
                ("2026-03-11",),
            ).fetchone()
            imported_photo = conn.execute(
                "SELECT path FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-03-11",),
            ).fetchone()

        self.assertAlmostEqual(existing["sleep_hours"], 7.0)
        self.assertEqual(existing["steps"], 8000)
        self.assertAlmostEqual(imported["sleep_hours"], 7.3)
        self.assertEqual(imported["steps"], 9100)
        self.assertAlmostEqual(imported["weight_kg"], 69.8)
        self.assertEqual(imported["photo_yn"], "Y")
        self.assertEqual(imported_photo["path"], "uploads/2026-03-11/progress.png")

    def test_backup_export_contains_db_and_uploads(self):
        self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-06-01",
                "sleep_hours": "7.2",
                "photo": (io.BytesIO(b"photo-bytes"), "photo.png"),
            },
            content_type="multipart/form-data",
        )

        res = self.client.get("/backup/export")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/zip")
        zbuf = io.BytesIO(res.data)
        with zipfile.ZipFile(zbuf, "r") as zf:
            names = zf.namelist()
        self.assertIn("tracker.db", names)
        self.assertIn("meta.json", names)
        self.assertTrue(any(n.startswith("uploads/2026-06-01/") for n in names))

    def test_backup_restore_reverts_to_snapshot(self):
        self.client.post(
            "/api/diet",
            json={"log_date": "2026-06-10", "sleep_hours": 7.0, "steps": 8000},
        )

        backup = self.client.get("/backup/export")
        self.assertEqual(backup.status_code, 200)
        backup_bytes = backup.data

        self.client.post(
            "/api/diet",
            json={"log_date": "2026-06-11", "sleep_hours": 9.0, "steps": 12000},
        )

        denied = self.client.post(
            "/backup/restore",
            data={"backup_file": (io.BytesIO(backup_bytes), "backup.zip")},
            content_type="multipart/form-data",
        )
        self.assertEqual(denied.status_code, 409)
        self.assertTrue((denied.get_json() or {}).get("needs_confirm"))

        restored = self.client.post(
            "/backup/restore",
            data={
                "backup_file": (io.BytesIO(backup_bytes), "backup.zip"),
                "restore_confirm": "1",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(restored.status_code, 200, restored.get_data(as_text=True))
        payload = restored.get_json()
        self.assertTrue(payload.get("ok"))

        state = self.client.get("/api/state?limit=30").get_json()
        dates = [r["log_date"] for r in state.get("diet", [])]
        self.assertIn("2026-06-10", dates)
        self.assertNotIn("2026-06-11", dates)

    def test_photo_replace_requires_confirmation_and_deletes_old_file(self):
        first = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-12",
                "photo": (io.BytesIO(b"first-photo"), "first.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))

        with self._db() as conn:
            old_rel = conn.execute(
                "SELECT path FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-02-12",),
            ).fetchone()["path"]
        old_abs = tracker.photo_rel_to_abs(old_rel)
        self.assertTrue(old_abs)
        self.assertTrue(Path(old_abs).exists())

        second = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-12",
                "photo": (io.BytesIO(b"second-photo"), "second.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(second.status_code, 409)
        payload = second.get_json()
        self.assertTrue(payload.get("needs_confirm"))
        self.assertIn("/uploads/", payload.get("existing_photo_url", ""))

        third = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-12",
                "photo_replace_confirm": "1",
                "photo": (io.BytesIO(b"second-photo"), "second.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(third.status_code, 200, third.get_data(as_text=True))

        with self._db() as conn:
            new_rel = conn.execute(
                "SELECT path FROM photo_log WHERE log_date = ? AND kind = 'progress';",
                ("2026-02-12",),
            ).fetchone()["path"]

        self.assertNotEqual(old_rel, new_rel)
        self.assertFalse(Path(old_abs).exists())
        self.assertTrue(Path(tracker.photo_rel_to_abs(new_rel)).exists())

    def test_uploaded_photo_is_served_via_upload_route(self):
        raw = b"png-like-content"
        res = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-16",
                "photo": (io.BytesIO(raw), "photo.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))

        state = self.client.get("/api/state?limit=30").get_json()
        row = next((r for r in state["diet"] if r["log_date"] == "2026-02-16"), None)
        self.assertIsNotNone(row)
        self.assertTrue(row["photo_url"].startswith("/uploads/"))

        pic = self.client.get(row["photo_url"])
        self.assertEqual(pic.status_code, 200)
        self.assertGreater(len(pic.data or b""), 0)
        pic.close()

    def test_save_progress_photo_uses_compressed_payload_when_available(self):
        original_compressor = tracker._compress_photo_bytes
        try:
            tracker.PHOTO_COMPRESSION_ENABLED = True

            def fake_compressor(raw_bytes, ext):
                self.assertEqual(raw_bytes, b"raw-photo")
                self.assertEqual(ext, ".png")
                return (b"compressed-photo", ".webp")

            tracker._compress_photo_bytes = fake_compressor
            storage = FileStorage(stream=io.BytesIO(b"raw-photo"), filename="avance.png")
            rel = tracker.save_progress_photo(storage, "2026-02-17")

            self.assertTrue(rel.endswith(".webp"), rel)
            saved_abs = tracker.photo_rel_to_abs(rel)
            self.assertTrue(saved_abs)
            self.assertEqual(Path(saved_abs).read_bytes(), b"compressed-photo")
        finally:
            tracker._compress_photo_bytes = original_compressor

    def test_save_progress_photo_falls_back_to_original_payload(self):
        original_compressor = tracker._compress_photo_bytes
        try:
            tracker.PHOTO_COMPRESSION_ENABLED = True
            tracker._compress_photo_bytes = lambda *_: None
            storage = FileStorage(stream=io.BytesIO(b"raw-photo-2"), filename="avance2.jpg")
            rel = tracker.save_progress_photo(storage, "2026-02-18")

            self.assertTrue(rel.endswith(".jpg"), rel)
            saved_abs = tracker.photo_rel_to_abs(rel)
            self.assertTrue(saved_abs)
            self.assertEqual(Path(saved_abs).read_bytes(), b"raw-photo-2")
        finally:
            tracker._compress_photo_bytes = original_compressor

    def test_invalid_photo_extension_returns_400(self):
        res = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-13",
                "photo": (io.BytesIO(b"content"), "bad.gif"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 400)
        payload = res.get_json()
        self.assertIn("Extensión", payload.get("error", ""))

    def test_payload_too_large_returns_413(self):
        tracker.APP.config["MAX_CONTENT_LENGTH"] = 1024 * 1024  # 1MB
        big = io.BytesIO(b"x" * (2 * 1024 * 1024))
        res = self.client.post(
            "/api/diet",
            data={
                "log_date": "2026-02-14",
                "photo": (big, "huge.jpg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 413)
        payload = res.get_json()
        self.assertIn("Máximo permitido", payload.get("error", ""))

    def test_photo_flag_y_without_photo_file_does_not_persist_as_y(self):
        res = self.client.post(
            "/api/diet",
            json={
                "log_date": "2026-02-15",
                "photo_yn": "Y",
                "sleep_hours": 7.0,
            },
        )
        self.assertEqual(res.status_code, 200)

        with self._db() as conn:
            row = conn.execute(
                "SELECT photo_yn FROM diet_log WHERE log_date = ?;",
                ("2026-02-15",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row["photo_yn"])

    def test_supplements_catalog_day_crud_and_export(self):
        create_a = self.client.post(
            "/api/supplements/config",
            json={
                "name": "Melatonina",
                "doses_per_day": 1,
                "active_yn": "Y",
                "notes": "Antes de dormir",
            },
        )
        self.assertEqual(create_a.status_code, 200, create_a.get_data(as_text=True))
        payload_a = create_a.get_json()
        self.assertEqual(payload_a["entry_mode"], "create")
        melatonina_id = int(payload_a["supplement"]["supplement_id"])

        create_b = self.client.post(
            "/api/supplements/config",
            json={
                "name": "Proteina Whey",
                "doses_per_day": 2,
                "active_yn": "Y",
            },
        )
        self.assertEqual(create_b.status_code, 200, create_b.get_data(as_text=True))
        whey_id = int(create_b.get_json()["supplement"]["supplement_id"])

        dup = self.client.post(
            "/api/supplements/config",
            json={"name": "melatonina", "doses_per_day": 1},
        )
        self.assertEqual(dup.status_code, 409)

        update_whey = self.client.post(
            "/api/supplements/config",
            json={
                "supplement_id": whey_id,
                "name": "Proteina Whey",
                "doses_per_day": 2,
                "active_yn": "N",
                "notes": "Post entreno",
            },
        )
        self.assertEqual(update_whey.status_code, 200, update_whey.get_data(as_text=True))
        self.assertEqual(update_whey.get_json()["entry_mode"], "edit")

        config_all = self.client.get("/api/supplements/config").get_json()
        self.assertTrue(config_all.get("ok"))
        self.assertEqual(len(config_all.get("supplements", [])), 2)

        config_active = self.client.get("/api/supplements/config?active_only=1").get_json()
        self.assertEqual(len(config_active.get("supplements", [])), 1)
        self.assertEqual(config_active["supplements"][0]["name"], "Melatonina")

        day_save = self.client.post(
            "/api/supplements/day",
            json={
                "log_date": "2026-07-01",
                "entries": [
                    {"supplement_id": melatonina_id, "doses_taken": 1, "notes": "OK"},
                    {"supplement_id": whey_id, "doses_taken": 2, "notes": "Doble toma"},
                ],
            },
        )
        self.assertEqual(day_save.status_code, 200, day_save.get_data(as_text=True))
        saved = day_save.get_json()
        self.assertEqual(saved["totals"]["target_doses"], 3)
        self.assertEqual(saved["totals"]["taken_doses"], 3)

        day_get = self.client.get("/api/supplements/day?log_date=2026-07-01").get_json()
        self.assertTrue(day_get.get("ok"))
        by_name = {item["name"]: item for item in day_get.get("entries", [])}
        self.assertIn("Melatonina", by_name)
        self.assertIn("Proteina Whey", by_name)
        self.assertEqual(by_name["Melatonina"]["doses_taken"], 1)
        self.assertEqual(by_name["Proteina Whey"]["doses_taken"], 2)

        deleted = self.client.delete(f"/api/supplements/config/{whey_id}")
        self.assertEqual(deleted.status_code, 200, deleted.get_data(as_text=True))

        day_after_delete = self.client.get("/api/supplements/day?log_date=2026-07-01").get_json()
        names_after = [item["name"] for item in day_after_delete.get("entries", [])]
        self.assertIn("Melatonina", names_after)
        self.assertNotIn("Proteina Whey", names_after)

    def test_plan_import_diet_and_fetch_day(self):
        csv_text = """date,calories_target_kcal,protein_target_g,carbs_target_g,fat_target_g,breakfast,snack_1,lunch,snack_2,dinner,notes
2026-08-01,2200,150,220,80,Huevos,Fruta,Pollo+arroz,Yogur,Pescado,Plan base
2026-08-02,2400,150,290,70,Avena,Queso,Carne+patata,Fruta,Tortilla,
"""
        res = self.client.post(
            "/api/plan/import/diet",
            data={"file": (io.BytesIO(csv_text.encode("utf-8")), "plan_diet.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        payload = res.get_json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["summary"]["total"], 2)
        self.assertEqual(payload["summary"]["imported"], 2)
        self.assertEqual(payload["summary"]["invalid"], 0)

        day = self.client.get("/api/plan/day?log_date=2026-08-01").get_json()
        self.assertTrue(day.get("ok"))
        self.assertEqual(day["log_date"], "2026-08-01")
        self.assertIsNotNone(day["diet"])
        self.assertAlmostEqual(day["diet"]["calories_target_kcal"], 2200.0)
        self.assertEqual(day["diet"]["breakfast"], "Huevos")
        self.assertFalse(day["coverage"]["has_workout_plan"])

    def test_plan_import_workout_and_adherence(self):
        sessions_csv = """date,session_id,session_type,warmup,class_sessions,cardio,mobility_cooldown,additional_exercises,notes
2026-08-03,A,pesas,Bici 10 min,,Caminata 20,Estirar 8,Abducciones,Dia fuerte
2026-08-03,B,clase,,, ,Movilidad suave,,Pilates
"""
        sessions_res = self.client.post(
            "/api/plan/import/workout-sessions",
            data={"file": (io.BytesIO(sessions_csv.encode("utf-8")), "sessions.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(sessions_res.status_code, 200, sessions_res.get_data(as_text=True))
        self.assertEqual(sessions_res.get_json()["summary"]["imported"], 2)

        exercises_csv = """date,session_id,exercise_order,exercise_name,target_sets,target_reps_min,target_reps_max,target_weight_kg,target_rpe,intensity_target,progression_weight_rule,progression_reps_rule
2026-08-03,A,1,Hip Thrust,4,5,8,120,8,RPE 7-8,+2.5kg,+1 rep
2026-08-03,A,2,Sentadilla,4,6,8,85,7.5,RPE 7-8,+2kg,+1 rep
"""
        exercises_res = self.client.post(
            "/api/plan/import/workout-exercises",
            data={"file": (io.BytesIO(exercises_csv.encode("utf-8")), "ex.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(exercises_res.status_code, 200, exercises_res.get_data(as_text=True))
        ex_payload = exercises_res.get_json()
        self.assertEqual(ex_payload["summary"]["imported"], 2)
        self.assertEqual(ex_payload["summary"]["invalid"], 0)

        day = self.client.get("/api/plan/day?log_date=2026-08-03").get_json()
        self.assertTrue(day.get("ok"))
        self.assertIsNone(day["diet"])
        self.assertTrue(day["coverage"]["has_workout_plan"])
        self.assertEqual(len(day["workout_sessions"]), 2)
        strength = next((s for s in day["workout_sessions"] if s["plan_session_id"] == "A"), None)
        self.assertIsNotNone(strength)
        self.assertEqual(len(strength["exercises"]), 2)
        self.assertEqual(strength["exercises"][0]["exercise_name"], "Hip Thrust")

        save_adherence = self.client.post(
            "/api/plan/adherence",
            json={
                "log_date": "2026-08-03",
                "diet_score": 0.5,
                "workout_score": 1,
                "notes": "Cumplido",
            },
        )
        self.assertEqual(save_adherence.status_code, 200, save_adherence.get_data(as_text=True))
        saved_payload = save_adherence.get_json()
        self.assertAlmostEqual(saved_payload["adherence"]["diet_score"], 0.5)
        self.assertAlmostEqual(saved_payload["adherence"]["workout_score"], 1.0)
        self.assertAlmostEqual(saved_payload["adherence"]["total_score"], 0.75)
        self.assertEqual(saved_payload["adherence_history"]["window_days"], 15)
        self.assertEqual(saved_payload["adherence_history"]["total_days"], 15)
        self.assertEqual(saved_payload["adherence_week"]["total_days"], 7)
        self.assertEqual(saved_payload["adherence_week"]["scored_days"], 1)

        bad_adherence = self.client.post(
            "/api/plan/adherence",
            json={"log_date": "2026-08-03", "diet_score": 0.7},
        )
        self.assertEqual(bad_adherence.status_code, 400)

        second_adherence = self.client.post(
            "/api/plan/adherence",
            json={
                "log_date": "2026-08-04",
                "diet_score": 1,
                "workout_score": 0,
                "notes": "sesion corta",
            },
        )
        self.assertEqual(second_adherence.status_code, 200, second_adherence.get_data(as_text=True))

        custom_window = self.client.get(
            "/api/plan/day?log_date=2026-08-04&adherence_days=7"
        ).get_json()
        self.assertEqual(custom_window["adherence_history"]["window_days"], 7)
        self.assertEqual(custom_window["adherence_history"]["total_days"], 7)
        self.assertEqual(custom_window["adherence_history"]["scored_days"], 2)
        self.assertEqual(len(custom_window["adherence_history"]["items"]), 2)
        self.assertEqual(custom_window["adherence_history"]["items"][0]["log_date"], "2026-08-04")
        self.assertEqual(custom_window["adherence_week"]["scored_days"], 2)
        self.assertAlmostEqual(custom_window["adherence_week"]["avg_total"], 0.625)
        self.assertAlmostEqual(custom_window["adherence_week"]["avg_diet"], 0.75)
        self.assertAlmostEqual(custom_window["adherence_week"]["avg_workout"], 0.5)

    def test_plan_import_workout_combined_csv(self):
        headers = list(tracker.PLAN_WORKOUT_COMBINED_FIELDS)

        def make_row(base=None, exercises=None):
            row = {k: "" for k in headers}
            for key, value in (base or {}).items():
                row[key] = value
            for idx, ex in enumerate(exercises or [], start=1):
                for suffix, value in ex.items():
                    row[f"exercise_{idx}_{suffix}"] = value
            return row

        rows = [
            make_row(
                {
                    "log_date": "2026-08-04",
                    "session_type": "pesas",
                    "warmup": "Bici",
                    "notes": "AM",
                },
                exercises=[
                    {
                        "name": "Hip Thrust",
                        "sets": "4",
                        "reps_min": "5",
                        "reps_max": "8",
                        "weight_kg": "120",
                        "rpe": "8",
                    },
                    {
                        "name": "Sentadilla",
                        "sets": "3",
                        "reps_min": "6",
                        "reps_max": "8",
                        "weight_kg": "85",
                        "rpe": "7.5",
                    },
                ],
            ),
            make_row(
                {
                    "log_date": "2026-08-04",
                    "session_type": "clase",
                    "class_sessions": "Pilates",
                    "notes": "PM",
                },
                exercises=[
                    {
                        "name": "No aplica",
                        "sets": "1",
                    }
                ],
            ),
            make_row(
                {
                    "log_date": "2026-08-04",
                    "session_type": "pesas",
                    "notes": "Noche",
                },
                exercises=[],
            ),
        ]

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        res = self.client.post(
            "/api/plan/import/workout",
            data={"file": (io.BytesIO(buf.getvalue().encode("utf-8")), "plan_workout.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        payload = res.get_json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["summary"]["total"], 3)
        self.assertEqual(payload["summary"]["imported"], 3)
        self.assertEqual(payload["summary"]["invalid"], 0)
        self.assertEqual(payload["summary"]["warned"], 1)

        day = self.client.get("/api/plan/day?log_date=2026-08-04").get_json()
        self.assertTrue(day.get("ok"))
        self.assertEqual(len(day["workout_sessions"]), 3)
        self.assertEqual(
            [s["plan_session_id"] for s in day["workout_sessions"]],
            ["S01", "S02", "S03"],
        )
        self.assertEqual(day["workout_sessions"][0]["session_type"], "pesas")
        self.assertEqual(len(day["workout_sessions"][0]["exercises"]), 2)
        self.assertEqual(day["workout_sessions"][1]["session_type"], "clase")
        self.assertEqual(len(day["workout_sessions"][1]["exercises"]), 0)
        self.assertEqual(day["workout_sessions"][2]["session_type"], "pesas")

    def test_plan_import_workout_combined_ignores_guided_hint_rows(self):
        headers = list(tracker.PLAN_WORKOUT_COMBINED_FIELDS)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"log_date": "#TYPE_HINT"})
        writer.writerow({"log_date": "#RULE_HINT"})
        writer.writerow(
            {
                "log_date": "2026-08-10",
                "session_type": "clase",
                "class_sessions": "Pilates 50 min",
                "notes": "Fila real importable",
            }
        )

        res = self.client.post(
            "/api/plan/import/workout",
            data={"file": (io.BytesIO(buf.getvalue().encode("utf-8")), "plan_workout.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(res.status_code, 200, res.get_data(as_text=True))
        payload = res.get_json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload["summary"]["total"], 1)
        self.assertEqual(payload["summary"]["imported"], 1)
        self.assertEqual(payload["summary"]["invalid"], 0)

        day = self.client.get("/api/plan/day?log_date=2026-08-10").get_json()
        self.assertTrue(day.get("ok"))
        self.assertEqual(len(day["workout_sessions"]), 1)
        self.assertEqual(day["workout_sessions"][0]["session_type"], "clase")

    def test_plan_template_downloads_include_templates_and_ai_instructions(self):
        workout_template = self.client.get("/export/template/plan-workout.csv")
        self.assertEqual(workout_template.status_code, 200)
        self.assertIn("text/csv", workout_template.headers.get("Content-Type", ""))
        workout_csv_text = workout_template.get_data(as_text=True)
        self.assertNotIn("#TYPE_HINT", workout_csv_text)
        self.assertNotIn("#RULE_HINT", workout_csv_text)
        self.assertIn("exercise_1_sets", workout_csv_text)

        ai_md = self.client.get("/export/template/plan-csv-ai-instructions.md")
        self.assertEqual(ai_md.status_code, 200)
        self.assertIn("text/markdown", ai_md.headers.get("Content-Type", ""))
        ai_md_text = ai_md.get_data(as_text=True)
        self.assertIn("System Prompt", ai_md_text)
        self.assertIn("plan_diet_template.csv", ai_md_text)
        self.assertIn("plan_workout_template.csv", ai_md_text)

        ai_diet = self.client.get("/export/template/plan-csv-ai-instructions-diet.md")
        self.assertEqual(ai_diet.status_code, 200)
        self.assertIn("text/markdown", ai_diet.headers.get("Content-Type", ""))
        ai_diet_text = ai_diet.get_data(as_text=True)
        self.assertIn("Instrucciones IA para CSV de Dieta", ai_diet_text)
        self.assertIn("responde SOLO con CSV crudo", ai_diet_text)

        ai_workout = self.client.get("/export/template/plan-csv-ai-instructions-workout.md")
        self.assertEqual(ai_workout.status_code, 200)
        self.assertIn("text/markdown", ai_workout.headers.get("Content-Type", ""))
        ai_workout_text = ai_workout.get_data(as_text=True)
        self.assertIn("Instrucciones IA para CSV de Entreno Planificado", ai_workout_text)
        self.assertIn("session_type", ai_workout_text)
        self.assertIn("solo `clase` o `pesas`", ai_workout_text)

    def test_plan_diet_delete_day_and_flush(self):
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO plan_day_diet (log_date, calories_target_kcal, breakfast)
                VALUES ('2026-09-01', 2200, 'Huevos');
                """
            )
            conn.execute(
                """
                INSERT INTO plan_day_diet (log_date, calories_target_kcal, breakfast)
                VALUES ('2026-09-02', 2400, 'Avena');
                """
            )
            conn.commit()

        delete_day = self.client.delete("/api/plan/diet/2026-09-01")
        self.assertEqual(delete_day.status_code, 200, delete_day.get_data(as_text=True))
        day_payload = delete_day.get_json()
        self.assertTrue(day_payload.get("ok"))
        self.assertEqual(day_payload.get("deleted_rows"), 1)

        with self._db() as conn:
            exists_day = conn.execute(
                "SELECT 1 FROM plan_day_diet WHERE log_date = '2026-09-01';"
            ).fetchone()
            remain_count = conn.execute(
                "SELECT COUNT(*) AS n FROM plan_day_diet;"
            ).fetchone()["n"]
        self.assertIsNone(exists_day)
        self.assertEqual(remain_count, 1)

        flush = self.client.delete("/api/plan/diet")
        self.assertEqual(flush.status_code, 200, flush.get_data(as_text=True))
        flush_payload = flush.get_json()
        self.assertTrue(flush_payload.get("ok"))
        self.assertEqual(flush_payload.get("deleted_rows"), 1)

        with self._db() as conn:
            final_count = conn.execute(
                "SELECT COUNT(*) AS n FROM plan_day_diet;"
            ).fetchone()["n"]
        self.assertEqual(final_count, 0)

    def test_plan_workout_delete_session_and_flush(self):
        with self._db() as conn:
            conn.execute(
                """
                INSERT INTO plan_day_workout_session (log_date, plan_session_id, session_type, notes)
                VALUES ('2026-09-03', 'S01', 'pesas', 'AM');
                """
            )
            conn.execute(
                """
                INSERT INTO plan_day_workout_session (log_date, plan_session_id, session_type, notes)
                VALUES ('2026-09-03', 'S02', 'clase', 'PM');
                """
            )
            conn.execute(
                """
                INSERT INTO plan_day_workout_exercise (log_date, plan_session_id, exercise_order, exercise_name)
                VALUES ('2026-09-03', 'S01', 1, 'Hip Thrust');
                """
            )
            conn.execute(
                """
                INSERT INTO plan_day_workout_exercise (log_date, plan_session_id, exercise_order, exercise_name)
                VALUES ('2026-09-03', 'S01', 2, 'Sentadilla');
                """
            )
            conn.commit()

        delete_one = self.client.delete("/api/plan/workout/2026-09-03/S01")
        self.assertEqual(delete_one.status_code, 200, delete_one.get_data(as_text=True))
        delete_payload = delete_one.get_json()
        self.assertTrue(delete_payload.get("ok"))
        self.assertEqual(delete_payload.get("deleted_sessions"), 1)
        self.assertEqual(delete_payload.get("deleted_exercises"), 2)

        with self._db() as conn:
            deleted_session = conn.execute(
                """
                SELECT 1
                FROM plan_day_workout_session
                WHERE log_date = '2026-09-03' AND plan_session_id = 'S01';
                """
            ).fetchone()
            deleted_children = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM plan_day_workout_exercise
                WHERE log_date = '2026-09-03' AND plan_session_id = 'S01';
                """
            ).fetchone()["n"]
            remaining_sessions = conn.execute(
                "SELECT COUNT(*) AS n FROM plan_day_workout_session;"
            ).fetchone()["n"]
        self.assertIsNone(deleted_session)
        self.assertEqual(deleted_children, 0)
        self.assertEqual(remaining_sessions, 1)

        flush = self.client.delete("/api/plan/workout")
        self.assertEqual(flush.status_code, 200, flush.get_data(as_text=True))
        flush_payload = flush.get_json()
        self.assertTrue(flush_payload.get("ok"))
        self.assertEqual(flush_payload.get("deleted_sessions"), 1)
        self.assertEqual(flush_payload.get("deleted_exercises"), 0)

        with self._db() as conn:
            final_sessions = conn.execute(
                "SELECT COUNT(*) AS n FROM plan_day_workout_session;"
            ).fetchone()["n"]
            final_exercises = conn.execute(
                "SELECT COUNT(*) AS n FROM plan_day_workout_exercise;"
            ).fetchone()["n"]
        self.assertEqual(final_sessions, 0)
        self.assertEqual(final_exercises, 0)

    def test_safe_delete_rejects_non_upload_paths(self):
        self.assertFalse(tracker.safe_delete_uploaded_photo("../etc/passwd"))
        self.assertFalse(tracker.safe_delete_uploaded_photo("static/not-uploads/file.jpg"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
