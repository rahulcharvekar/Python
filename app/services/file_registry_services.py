import sqlite3
from app.core.config import settings
from datetime import datetime
from app.utils.Logging.logger import logger 


def init_db():
    try:
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
    except sqlite3.Error as e:
        logger.error(f"An error occurred while initializing the database: {e}")


def add_file_record(file_name, file_hash, vector_path):
    try:
        """Add a new file entry to the registry."""
        init_db()  # Ensure the database is initialized    
        with sqlite3.connect(settings.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_registry (file_name, file_hash, vector_path, uploaded_at)
                VALUES (?, ?, ?, ?)
            """, (file_name, file_hash, vector_path, datetime.now().isoformat()))
            conn.commit()
    except sqlite3.IntegrityError:
        logger.error(f"File with hash {file_hash} already exists in the registry.")


def get_file_by_hash(file_hash):
    try:
        """Check if a file with the given hash already exists."""
        with sqlite3.connect(settings.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_registry WHERE file_hash = ?", (file_hash,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"An error occurred while fetching file by hash {file_hash}: {e}")
        return None 


def get_file_by_name(file_name):
    try:
        """Check if a file with the given name already exists."""
        with sqlite3.connect(settings.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_registry WHERE file_name = ?", (file_name,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"An error occurred while fetching file by name {file_name}: {e}")

def delete_file_record(file_name):
    try:
        """Check if a file with the given hash already exists."""
        with sqlite3.connect(settings.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("delete FROM file_registry WHERE file_name = ?", (file_name,))
            return cursor.fetchone()                                                                            
    except sqlite3.Error as e:
        logger.error(f"An error occurred while deleting file by name {file_name}: {e}")
        return None 