import sqlite3
from app.core.config import settings
from datetime import datetime



def init_db():
    """Create the database and table if they don't exist."""
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_hash TEXT UNIQUE NOT NULL,
                vector_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
        """)
        conn.commit()


def add_file_record(file_name, file_hash, vector_path):
    """Add a new file entry to the registry."""
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO file_registry (file_name, file_hash, vector_path, uploaded_at)
            VALUES (?, ?, ?, ?)
        """, (file_name, file_hash, vector_path, datetime.now().isoformat()))
        conn.commit()


def get_file_by_hash(file_hash):
    """Check if a file with the given hash already exists."""
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM file_registry WHERE file_hash = ?", (file_hash,))
        return cursor.fetchone()


def get_file_by_name(file_name):
    """Check if a file with the given name already exists."""
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM file_registry WHERE file_name = ?", (file_name,))
        return cursor.fetchone()

def delete_file_record(file_name):
    """Check if a file with the given hash already exists."""
    with sqlite3.connect(settings.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("delete FROM file_registry WHERE file_name = ?", (file_name,))
        return cursor.fetchone()