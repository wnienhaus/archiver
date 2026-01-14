import unittest
import shutil
import tempfile
import sys
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# Add project root to sys.path to ensure we can import the archiver package
sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.commands import cmd_init, cmd_add, cmd_verify, cmd_scan, cmd_status
from archiver.database import get_db_path, DB_DIR_NAME, get_connection
from archiver.utils import calculate_file_hash

class TestArchiver(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the archive root
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        
        # Create a source directory with some files
        self.source_dir = Path(tempfile.mkdtemp())
        self.file1 = self.source_dir / "file1.txt"
        self.file1.write_text("Content 1")
        
        self.subdir = self.source_dir / "subdir"
        self.subdir.mkdir()
        self.file2 = self.subdir / "file2.txt"
        self.file2.write_text("Content 2")

        # Suppress stdout/stderr for clean test output
        self.suppress_output = patch('sys.stdout', new=StringIO())
        self.suppress_error = patch('sys.stderr', new=StringIO())
        self.suppress_output.start()
        self.suppress_error.start()

    def tearDown(self):
        self.suppress_output.stop()
        self.suppress_error.stop()
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.source_dir)

    def test_init_success(self):
        """Test successful initialization."""
        cmd_init(self.root_path)
        db_path = get_db_path(self.root_path)
        self.assertTrue(db_path.exists())
        self.assertTrue((self.root_path / DB_DIR_NAME).is_dir())

    def test_init_fail_hidden_file(self):
        """Test init fails if hidden file exists in root."""
        (self.root_path / ".secret").touch()
        
        with self.assertRaises(SystemExit):
            cmd_init(self.root_path)

    def test_init_idempotent(self):
        """Test init is safe to run twice."""
        cmd_init(self.root_path)
        cmd_init(self.root_path)
        # Check that we haven't crashed and DB still exists
        self.assertTrue(get_db_path(self.root_path).exists())

    def test_add_basic(self):
        """Test adding files."""
        cmd_init(self.root_path)
        
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        dest_file = self.root_path / "docs" / "file1.txt"
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_text(), "Content 1")
        
        # Verify DB
        db_path = get_db_path(self.root_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path, hash FROM files")
        rows = cursor.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "docs/file1.txt")
        conn.close()

    def test_add_recursive(self):
        """Test adding directories recursively."""
        cmd_init(self.root_path)
        
        cmd_add(self.root_path, self.source_dir, "backup", False, False, False)
        
        self.assertTrue((self.root_path / "backup/file1.txt").exists())
        self.assertTrue((self.root_path / "backup/subdir/file2.txt").exists())
        
        db_path = get_db_path(self.root_path)
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute("SELECT count(*) FROM files")
        self.assertEqual(c.fetchone()[0], 2)
        conn.close()

    def test_add_duplicate_interactive_reject(self):
        """Test rejecting a duplicate interactively."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        # Try adding again, mock input 'n'
        with patch('builtins.input', return_value='n'):
            cmd_add(self.root_path, self.file1, "docs_copy", False, False, False)
            
        # Should not exist
        self.assertFalse((self.root_path / "docs_copy" / "file1.txt").exists())

    def test_add_duplicate_interactive_accept(self):
        """Test accepting a duplicate interactively."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        # Try adding again, mock input 'y'
        with patch('builtins.input', return_value='y'):
            cmd_add(self.root_path, self.file1, "docs_copy", False, False, False)
            
        self.assertTrue((self.root_path / "docs_copy" / "file1.txt").exists())
        
        # Check DB has 2 entries
        conn = get_connection(get_db_path(self.root_path))
        c = conn.cursor()
        c.execute("SELECT count(*) FROM files")
        self.assertEqual(c.fetchone()[0], 2)
        conn.close()

    def test_add_duplicate_flags(self):
        """Test --accept-duplicates and --skip-duplicates flags."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        # Test Skip
        cmd_add(self.root_path, self.file1, "skipped", False, False, True)
        self.assertFalse((self.root_path / "skipped" / "file1.txt").exists())
        
        # Test Accept
        cmd_add(self.root_path, self.file1, "accepted", False, True, False)
        self.assertTrue((self.root_path / "accepted" / "file1.txt").exists())

    def test_add_overwrite_protection(self):
        """Test that existing files are not overwritten."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        with patch('builtins.input', return_value='y'):
            # Try to add to SAME location
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                cmd_add(self.root_path, self.file1, "docs", False, False, False)
            
            self.assertIn("Destination file already exists", captured_output.getvalue())

    def test_verify_integrity(self):
        """Test verify command with healthy and corrupted files."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        # Healthy
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            cmd_verify(self.root_path)
        self.assertIn("All files OK", captured_output.getvalue())
        
        # Corrupt (modify content, same size to force hash check)
        dest_file = self.root_path / "docs" / "file1.txt"
        dest_file.write_text("Content X") # Same length as "Content 1"
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            cmd_verify(self.root_path)
        self.assertIn("CORRUPTED (Hash mismatch)", captured_output.getvalue())
        
        # Missing
        dest_file.unlink()
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            cmd_verify(self.root_path)
        self.assertIn("MISSING", captured_output.getvalue())

    def test_scan_rebuild(self):
        """Test rebuilding database from disk."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        # Delete DB
        db_path = get_db_path(self.root_path)
        shutil.rmtree(db_path.parent)
        
        # Scan
        cmd_scan(self.root_path)
        
        self.assertTrue(db_path.exists())
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute("SELECT path FROM files")
        rows = c.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "docs/file1.txt")
        conn.close()

    def test_status(self):
        """Test status output."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            cmd_status(self.root_path)
        
        output = captured_output.getvalue()
        self.assertIn("Total Files: 1", output)
        self.assertIn("Unverified Files: 1", output)

if __name__ == '__main__':
    unittest.main()
