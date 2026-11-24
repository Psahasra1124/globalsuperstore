import os
import re
import sqlite3
from pathlib import Path
from time import monotonic

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def get_connection():
    if os.getenv("DB_TYPE","sqlite").lower()=="mysql":
        try:
            import mysql.connector
            return mysql.connector.connect(host=os.getenv("MYSQL_HOST","localhost"),
                port=int(os.getenv("MYSQL_PORT","3306")),user=os.getenv("MYSQL_USER","root"),
                password=os.getenv("MYSQL_PASSWORD",""),database=os.getenv("MYSQL_DATABASE","superstore"))
        except Exception as e:
            raise RuntimeError(f"MySQL connection failed: {e}. Set DB_TYPE=sqlite for local fallback.")
    database_directory=ROOT/"database"
    database_directory.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(database_directory/"superstore.db",check_same_thread=False)
    return conn

def initialize_database(conn,df=None):
    if df is None: return
    df.to_sql("orders",conn,if_exists="replace",index=False)

def load_to_database(df):
    conn=get_connection()
    initialize_database(conn,df)
    return conn


def load_to_sqlite(df):
    database_directory = ROOT / "database"
    database_directory.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_directory / "superstore.db", timeout=10)
    try:
        initialize_database(conn, df)
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


def load_to_readonly_sqlite(df):
    connection = load_to_sqlite(df)
    connection.close()
    database_path = (ROOT / "database" / "superstore.db").resolve()
    return sqlite3.connect(
        database_path.as_uri() + "?mode=ro",
        uri=True,
        timeout=5,
    )


def _read_only_authorizer(action, first, second, database, trigger):
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_RECURSIVE,
    }
    safe_functions = {
        "abs",
        "avg",
        "coalesce",
        "count",
        "dense_rank",
        "first_value",
        "ifnull",
        "lag",
        "last_value",
        "lead",
        "length",
        "lower",
        "max",
        "min",
        "nullif",
        "ntile",
        "percent_rank",
        "rank",
        "replace",
        "round",
        "row_number",
        "strftime",
        "substr",
        "sum",
        "trim",
        "upper",
    }
    if database not in (None, "main"):
        return sqlite3.SQLITE_DENY
    if trigger is not None and action not in {
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if first == "orders" else sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK if (second or "").lower() in safe_functions else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def query_df(conn,sql):
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("Read-only SQL analytics are available only in SQLite.")
    statement = re.sub(
        r"\A(?:\s|--[^\r\n]*(?:\r?\n|\Z)|/\*.*?\*/)*",
        "",
        str(sql or ""),
        count=1,
        flags=re.DOTALL,
    )
    if not re.match(r"(?:SELECT|WITH)\b", statement, flags=re.IGNORECASE):
        raise ValueError("Only SELECT queries, including SELECT-based CTEs, are allowed.")
    deadline = monotonic() + 5
    conn.set_authorizer(_read_only_authorizer)
    conn.set_progress_handler(lambda: int(monotonic() > deadline), 10_000)
    try:
        cursor = conn.execute(sql)
        if cursor.description is None:
            raise ValueError("Only read-only SELECT queries are allowed.")
        columns = [item[0] for item in cursor.description]
        rows = cursor.fetchmany(10_001)
        if len(rows) > 10_000:
            raise ValueError("Query returned more than 10,000 rows. Add a LIMIT clause.")
        return pd.DataFrame.from_records(rows, columns=columns)
    finally:
        conn.set_authorizer(None)
        conn.set_progress_handler(None, 0)
