import unittest
import tempfile
import shutil
import sqlite3
from pathlib import Path
from archiver.database import get_connection, init_db

class TestSqliteSettings(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_wal_mode_and_synchronous(self):
        # init_db uses get_connection
        init_db(self.db_path)
        
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        self.assertEqual(journal_mode.lower(), "wal")
        
        cursor.execute("PRAGMA synchronous;")
        synchronous = cursor.fetchone()[0]
        # NORMAL is 1, FULL is 2, OFF is 0
        self.assertEqual(synchronous, 1)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
