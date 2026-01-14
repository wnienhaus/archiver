import unittest
import shutil
import tempfile
import sys
import sqlite3
from pathlib import Path
from unittest.mock import patch
from io import StringIO

from archiver.commands import cmd_init, cmd_scan, cmd_add
from archiver.database import get_db_path, get_connection

class TestScanProtection(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        self.file1 = self.root_path / "file1.txt"
        self.file1.write_text("Content 1")

        # Suppress output
        self.suppress_output = patch('sys.stdout', new=StringIO())
        self.suppress_error = patch('sys.stderr', new=StringIO())
        self.suppress_output.start()
        self.suppress_error.start()

    def tearDown(self):
        self.suppress_output.stop()
        self.suppress_error.stop()
        shutil.rmtree(self.test_dir)

    def test_scan_fails_on_populated_db_without_resume(self):
        # 1. Init and populate DB
        cmd_init(self.root_path)
        # Scan once to populate (resume=False is fine here because DB is empty)
        cmd_scan(self.root_path, resume=False)

        # Check DB has content
        db_path = get_db_path(self.root_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM files")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

        # 2. Try to scan again without resume
        # This should fail with SystemExit now (according to new requirement)
        with self.assertRaises(SystemExit):
             cmd_scan(self.root_path, resume=False)

    def test_scan_succeeds_with_resume_on_populated_db(self):
        cmd_init(self.root_path)
        cmd_scan(self.root_path, resume=False)

        # Should not raise
        cmd_scan(self.root_path, resume=True)

    def test_scan_succeeds_on_empty_db(self):
        cmd_init(self.root_path)
        # DB is empty
        cmd_scan(self.root_path, resume=False)
