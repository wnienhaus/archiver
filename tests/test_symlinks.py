import unittest
import shutil
import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.commands import cmd_init, cmd_add, cmd_verify, cmd_scan
from archiver.database import get_db_path, get_connection

class TestSymlinks(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        
        self.source_dir = Path(tempfile.mkdtemp())
        self.target_file = self.source_dir / "target.txt"
        self.target_file.write_text("Target Content")
        
        self.symlink = self.source_dir / "link.txt"
        self.symlink.symlink_to(self.target_file.name)

        self.suppress_output = patch('sys.stdout', new=StringIO())
        self.suppress_output.start()

    def tearDown(self):
        self.suppress_output.stop()
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.source_dir)

    def test_add_symlink_preserved(self):
        """Test that adding a symlink preserves it as a symlink."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.symlink, "links", False, False, False)
        
        dest_link = self.root_path / "links" / "link.txt"
        
        # This assertion is expected to fail currently because it will be a regular file
        self.assertTrue(dest_link.is_symlink(), "Archived item should be a symlink")
        self.assertEqual(os.readlink(dest_link), "target.txt", "Symlink target should be preserved")

    def test_verify_symlink(self):
        """Test that verify works for symlinks."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.symlink, "links", False, False, False)
        
        # Verify should pass (checking stdout for success message)
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cmd_verify(self.root_path)
            self.assertIn("All files OK", fake_out.getvalue())

    def test_scan_symlink(self):
        """Test that scanning rebuilds DB correctly for symlinks."""
        cmd_init(self.root_path)
        cmd_add(self.root_path, self.symlink, "links", False, False, False)
        
        # Wipe DB
        shutil.rmtree(get_db_path(self.root_path).parent)
        
        # Scan
        cmd_scan(self.root_path)
        
        db_path = get_db_path(self.root_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT hash, size FROM files")
        row = cursor.fetchone()
        conn.close()
        
        # Check that we found the file
        self.assertIsNotNone(row)

if __name__ == '__main__':
    unittest.main()
