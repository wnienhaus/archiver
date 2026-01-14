import unittest
import shutil
import tempfile
import sys
import sqlite3
from pathlib import Path
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.commands import cmd_init, cmd_scan, cmd_add
from archiver.database import get_db_path, get_connection

class TestScanResume(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        self.file1 = self.root_path / "file1.txt"
        self.file1.write_text("Content 1")
        self.file2 = self.root_path / "file2.txt"
        self.file2.write_text("Content 2")

        # Suppress output
        self.suppress_output = patch('sys.stdout', new=StringIO())
        self.suppress_error = patch('sys.stderr', new=StringIO())
        self.suppress_output.start()
        self.suppress_error.start()

    def tearDown(self):
        self.suppress_output.stop()
        self.suppress_error.stop()
        shutil.rmtree(self.test_dir)

    def test_scan_resume(self):
        cmd_init(self.root_path)

        # Manually run a full scan first to populate DB
        cmd_scan(self.root_path, resume=False)

        # Verify both files are in DB
        db_path = get_db_path(self.root_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path, id FROM files ORDER BY path")
        rows = cursor.fetchall()
        self.assertEqual(len(rows), 2)
        id_file1_orig = rows[0][1] # file1.txt

        conn.close()

        # Add a 3rd file to disk (but not DB)
        file3 = self.root_path / "file3.txt"
        file3.write_text("Content 3")

        # Run scan with resume=True
        cmd_scan(self.root_path, resume=True)

        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path, id FROM files ORDER BY path")
        rows = cursor.fetchall()

        # Should have 3 files now
        self.assertEqual(len(rows), 3)

        # Check that file1.txt has the SAME ID as before (meaning it wasn't deleted and re-inserted)
        # file1.txt should be first if sorted by path
        self.assertEqual(rows[0][0], "file1.txt")
        self.assertEqual(rows[0][1], id_file1_orig)

        # file3.txt should be present
        self.assertEqual(rows[2][0], "file3.txt")

        conn.close()

if __name__ == '__main__':
    unittest.main()
