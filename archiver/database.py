import sqlite3
import os
from pathlib import Path

DB_DIR_NAME = ".archive-index"
DB_NAME = "archive.db"

def get_db_path(root_path: Path, db_path_override: Path = None) -> Path:
    if db_path_override:
        return db_path_override
    return root_path / DB_DIR_NAME / DB_NAME

def init_db(db_path: Path):
    """Initialize the database schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        size INTEGER NOT NULL,
        hash TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_verified TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hash_index(
        hash TEXT NOT NULL,
        size INTEGER NOT NULL,
        file_id INTEGER NOT NULL,
        FOREIGN KEY(file_id) REFERENCES files(id)
    )
    """)
    
    # Adding an index for performance as per common sense, though spec didn't explicitly ask for the CREATE INDEX statement, 
    # it implies it's an index.
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash_size ON hash_index(hash, size)")
    
    conn.commit()
    return conn

def get_connection(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)
