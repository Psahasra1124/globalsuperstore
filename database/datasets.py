import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS_DATABASE = Path(__file__).resolve().parent / "system.db"
UPLOAD_DIRECTORY = ROOT / "data" / "uploads"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect():
    DATASETS_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATASETS_DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_dataset_db():
    DATASETS_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATASETS_DATABASE, timeout=10)
    cleanup_required = False
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA secure_delete = ON")
        connection.execute("BEGIN IMMEDIATE")
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                columns_json TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        if "datasets" in table_names:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(datasets)")
            }
            if "uploaded_by" in columns:
                cleanup_required = True
                connection.execute(
                    """
                    CREATE TABLE datasets_without_uploader (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_name TEXT NOT NULL,
                        stored_path TEXT NOT NULL,
                        sha256 TEXT NOT NULL,
                        uploaded_at TEXT NOT NULL,
                        row_count INTEGER NOT NULL,
                        columns_json TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO datasets_without_uploader
                        (id, original_name, stored_path, sha256, uploaded_at,
                         row_count, columns_json, is_active)
                    SELECT id, original_name, stored_path, sha256, uploaded_at,
                           row_count, columns_json, is_active
                    FROM datasets
                    """
                )
                connection.execute("DROP TABLE datasets")
                connection.execute(
                    "ALTER TABLE datasets_without_uploader RENAME TO datasets"
                )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        auth_tables = ("activity_log", "login_attempts", "users")
        cleanup_required = cleanup_required or any(
            table in table_names for table in auth_tables
        )
        for table in auth_tables:
            connection.execute(f"DROP TABLE IF EXISTS {table}")
        connection.commit()
        if cleanup_required:
            connection.execute("VACUUM")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_uploaded_dataset(original_name, content, row_count, columns):
    initialize_dataset_db()
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise ValueError("Only CSV and XLSX datasets are supported.")
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The uploaded dataset is empty or exceeds the 100 MB limit.")

    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    stored_name = (
        f"{digest[:16]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{suffix}"
    )
    target = UPLOAD_DIRECTORY / stored_name
    if target.exists():
        raise ValueError("This exact dataset has already been uploaded.")
    target.write_bytes(content)
    relative_path = target.relative_to(ROOT).as_posix()
    try:
        with _connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO datasets
                    (original_name, stored_path, sha256, uploaded_at, row_count, columns_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    Path(original_name).name[:255],
                    relative_path,
                    digest,
                    _now(),
                    int(row_count),
                    json.dumps(list(columns), ensure_ascii=True),
                ),
            )
            return int(cursor.lastrowid)
    except Exception:
        target.unlink(missing_ok=True)
        raise


def list_datasets():
    initialize_dataset_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, original_name, stored_path, sha256, uploaded_at,
                   row_count, columns_json, is_active
            FROM datasets
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_dataset_path(dataset_id):
    initialize_dataset_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT stored_path FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if not row:
            raise ValueError("Dataset upload record no longer exists.")
        return _resolve_uploaded_path(row["stored_path"])


def _resolve_uploaded_path(relative_path):
    path = (ROOT / relative_path).resolve()
    try:
        path.relative_to(UPLOAD_DIRECTORY.resolve())
    except ValueError as error:
        raise ValueError("Dataset path is outside the managed upload directory.") from error
    if path.suffix.lower() not in {".csv", ".xlsx"} or not path.is_file():
        raise ValueError("Managed dataset file is missing or has an unsupported type.")
    return path


def activate_dataset(dataset_id):
    initialize_dataset_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT stored_path, sha256 FROM datasets WHERE id = ?",
            (dataset_id,),
        ).fetchone()
        if not row:
            raise ValueError("Dataset upload record no longer exists.")
        path = _resolve_uploaded_path(row["stored_path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("The uploaded dataset changed after validation; upload it again.")
        connection.execute("UPDATE datasets SET is_active = 0")
        connection.execute("UPDATE datasets SET is_active = 1 WHERE id = ?", (dataset_id,))
        connection.execute(
            """
            INSERT INTO settings (key, value) VALUES ('active_dataset', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (row["stored_path"],),
        )
        return path


def get_active_dataset_path():
    initialize_dataset_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = 'active_dataset'"
        ).fetchone()
        if not row:
            return None
        return _resolve_uploaded_path(row["value"])
