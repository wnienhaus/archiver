import unittest
import shutil
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch
from archiver.commands import cmd_status
from archiver.database import init_db, get_connection

class TestIndexMigration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        self.db_path = self.root_path / ".archive-index" / "archive.db"
        
        # Initialize properly first to get tables
        init_db(self.db_path)
        
        # Manually drop the index to simulate old DB
        conn = get_connection(self.db_path)
        conn.execute("DROP INDEX IF EXISTS idx_files_path")
        conn.commit()
        conn.close()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_prompt_yes_creates_index(self):
        # Simulate user saying 'y'
        with patch('builtins.input', return_value='y'):
            cmd_status(self.root_path)
            
        # Verify index exists
        conn = get_connection(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_files_path'")
        self.assertIsNotNone(c.fetchone())
        conn.close()

    def test_prompt_no_does_not_create_index(self):
        # Simulate user saying 'n'
        with patch('builtins.input', return_value='n'):
            cmd_status(self.root_path)
            
        # Verify index does NOT exist
        conn = get_connection(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_files_path'")
        self.assertIsNone(c.fetchone())
        conn.close()

if __name__ == "__main__":
    unittest.main()
