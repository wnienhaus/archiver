import unittest
import os
import shutil
import tempfile
from pathlib import Path
from archiver.commands import cmd_init, cmd_add, cmd_scan
from archiver.database import get_connection, get_db_path

class TestDSStore(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir) / "archive"
        self.root_path.mkdir()
        self.source_path = Path(self.test_dir) / "source"
        self.source_path.mkdir()
        cmd_init(self.root_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_ds_store_excluded_from_add(self):
        # Create a .DS_Store file
        ds_store = self.source_path / ".DS_Store"
        ds_store.write_text("dummy")
        
        # Create a regular file
        regular_file = self.source_path / "regular.txt"
        regular_file.write_text("content")

        # Add the source directory
        cmd_add(self.root_path, self.source_path, "subdir", non_interactive=True, accept_duplicates=False, skip_duplicates=False)

        # Check if .DS_Store was archived
        conn = get_connection(get_db_path(self.root_path))
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM files WHERE path LIKE '%.DS_Store'")
        results = cursor.fetchall()
        
        self.assertEqual(len(results), 0, f".DS_Store should not be archived, but found: {results}")

    def test_ds_store_excluded_from_scan(self):
        # Manually put a .DS_Store file in the archive (simulating it being there before the rule)
        ds_store = self.root_path / "subdir" / ".DS_Store"
        ds_store.parent.mkdir(parents=True, exist_ok=True)
        ds_store.write_text("dummy")
        
        # Run scan
        cmd_scan(self.root_path)

        # Check if .DS_Store was indexed
        conn = get_connection(get_db_path(self.root_path))
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM files WHERE path LIKE '%.DS_Store'")
        results = cursor.fetchall()
        
        self.assertEqual(len(results), 0, f".DS_Store should not be indexed during scan, but found: {results}")

    def test_ds_store_explicit_add_skipped(self):
        # Create a .DS_Store file
        ds_store = self.source_path / ".DS_Store"
        ds_store.write_text("dummy")

        # Try to add it explicitly
        cmd_add(self.root_path, ds_store, "subdir", non_interactive=True, accept_duplicates=False, skip_duplicates=False)

        # Check if it was archived
        conn = get_connection(get_db_path(self.root_path))
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM files WHERE path LIKE '%.DS_Store'")
        results = cursor.fetchall()
        
        self.assertEqual(len(results), 0, f"Explicitly added .DS_Store should not be archived, but found: {results}")

    def test_init_allows_ds_store(self):
        # Create a new directory with a .DS_Store
        new_root = Path(self.test_dir) / "new_archive"
        new_root.mkdir()
        (new_root / ".DS_Store").write_text("dummy")
        
        # This should not raise SystemExit
        cmd_init(new_root)
        
        self.assertTrue((new_root / ".archive-index").exists())

if __name__ == "__main__":
    unittest.main()
