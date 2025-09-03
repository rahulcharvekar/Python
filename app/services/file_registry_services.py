import sqlite3
from datetime import datetime
from typing import Optional, Any

from app.core.config import settings
from app.utils.Logging.logger import logger


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS file_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_hash TEXT UNIQUE NOT NULL,
    vector_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
)
"""


def _connect(row_factory: Optional[Any] = None) -> sqlite3.Connection:
    """Create a DB connection with consistent PRAGMA settings."""
    conn = sqlite3.connect(settings.DB_PATH, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=TRUNCATE;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn


def _execute(query: str, params: tuple = (), *, fetch: Optional[str] = None, row_factory: Optional[Any] = None):
    """Execute a SQL statement with optional fetch-one/all support.

    fetch: None | "one" | "all"
    """
    try:
        with _connect(row_factory=row_factory) as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            conn.commit()
            return None
    except sqlite3.Error as e:
        raise e


def init_db() -> None:
    """Create the database and table if they don't exist."""
    try:
        _execute(CREATE_TABLE_SQL)
    except sqlite3.Error as e:
        logger.error(f"An error occurred while initializing the database: {e}")


def add_file_record(file_name: str, file_hash: str, vector_path: str) -> None:
    """Add a new file entry to the registry."""
    try:
        init_db()
        _execute(
            """
            INSERT INTO file_registry (file_name, file_hash, vector_path, uploaded_at)
            VALUES (?, ?, ?, ?)
            """,
            (file_name, file_hash, vector_path, datetime.now().isoformat()),
        )
    except sqlite3.IntegrityError:
        logger.error(f"File with hash {file_hash} already exists in the registry.")
    except sqlite3.Error as e:
        logger.error(f"An error occurred while adding file record: {e}")


def get_file_by_hash(file_hash: str):
    """Fetch the file row by hash (returns a tuple/Row or None)."""
    try:
        return _execute(
            "SELECT * FROM file_registry WHERE file_hash = ?",
            (file_hash,),
            fetch="one",
        )
    except sqlite3.Error as e:
        logger.error(f"An error occurred while fetching file by hash {file_hash}: {e}")
        return None


def get_file_by_name(file_name: str):
    """Fetch the file row by name (returns a tuple/Row or None)."""
    try:
        return _execute(
            "SELECT * FROM file_registry WHERE file_name = ?",
            (file_name,),
            fetch="one",
        )
    except sqlite3.Error as e:
        logger.error(f"An error occurred while fetching file by name {file_name}: {e}")
        return None


def get_all_files():
    """Return a list of dicts representing all file rows."""
    try:
        rows = _execute(
            "SELECT * FROM file_registry",
            fetch="all",
            row_factory=sqlite3.Row,
        )
        return [dict(row) for row in (rows or [])]
    except sqlite3.Error as e:
        logger.error(f"An error occurred while fetching all files: {e}")
        return None


def delete_file_record(file_name: str):
    """Delete a file by name. Returns None (matches prior behavior)."""
    try:
        logger.info(f"Deleting file record for {file_name}")
        _execute("DELETE FROM file_registry WHERE file_name = ?", (file_name,))
        return None
    except sqlite3.Error as e:
        logger.error(f"An error occurred while deleting file by name {file_name}: {e}")
        return None
