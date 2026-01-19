import unittest
import shutil
import tempfile
import os
from pathlib import Path
from archiver.commands import cmd_init, cmd_add, cmd_scan
from archiver.database import get_db_path, get_connection

class TestDotfilesRoot(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir) / "archive"
        self.root_path.mkdir()
        self.source_path = Path(self.test_dir) / "source"
        self.source_path.mkdir()
        cmd_init(self.root_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_add_root_dotfile_skipped(self):
        # Create a dotfile
        dotfile = self.source_path / ".env"
        dotfile.write_text("secret")
        
        # Try to add to root
        cmd_add(self.root_path, dotfile, "", False, False, False)
        
        # Verify it's NOT in the file system
        self.assertFalse((self.root_path / ".env").exists())
        
        # Verify NOT in DB
        conn = get_connection(get_db_path(self.root_path))
        c = conn.cursor()
        c.execute("SELECT count(*) FROM files WHERE path='.env'")
        self.assertEqual(c.fetchone()[0], 0)
        conn.close()

    def test_add_nested_dotfile_allowed(self):
        # Create a subdir with dotfile
        subdir = self.source_path / "subdir"
        subdir.mkdir()
        dotfile = subdir / ".env"
        dotfile.write_text("secret")
        
        # Add subdir to root
        cmd_add(self.root_path, subdir, "subdir", False, False, False)
        
        # Verify IT IS in the file system
        self.assertTrue((self.root_path / "subdir" / ".env").exists())
        
        # Verify IT IS in DB
        conn = get_connection(get_db_path(self.root_path))
        c = conn.cursor()
        c.execute("SELECT count(*) FROM files WHERE path='subdir/.env'")
        self.assertEqual(c.fetchone()[0], 1)
        conn.close()

    def test_add_dotdir_at_root_skipped(self):
        # Create a dotdir
        dotdir = self.source_path / ".git"
        dotdir.mkdir()
        (dotdir / "config").write_text("stuff")
        
        # Try to add dotdir to root
        cmd_add(self.root_path, dotdir, "", False, False, False)
        
        # Verify skipped
        self.assertFalse((self.root_path / ".git").exists())

    def test_scan_ignores_root_dotfiles(self):
        # Manually create a dotfile in root
        (self.root_path / ".manual").write_text("ignore me")
        
        # Manually create a dotdir in root
        (self.root_path / ".hidden").mkdir()
        (self.root_path / ".hidden" / "file").write_text("content")
        
        # Create a valid file
        (self.root_path / "valid.txt").write_text("valid")
        
        cmd_scan(self.root_path)
        
        conn = get_connection(get_db_path(self.root_path))
        c = conn.cursor()
        
        # Check valid file
        c.execute("SELECT count(*) FROM files WHERE path='valid.txt'")
        self.assertEqual(c.fetchone()[0], 1)
        
        # Check dotfile
        c.execute("SELECT count(*) FROM files WHERE path='.manual'")
        self.assertEqual(c.fetchone()[0], 0)
        
        # Check file inside dotdir
        c.execute("SELECT count(*) FROM files WHERE path LIKE '.hidden%'")
        self.assertEqual(c.fetchone()[0], 0)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
