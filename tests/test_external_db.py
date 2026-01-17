import unittest
import shutil
import tempfile
import sqlite3
from pathlib import Path
from archiver.commands import cmd_init, cmd_add, cmd_verify, cmd_status
from archiver.database import get_db_path, DB_DIR_NAME

class TestExternalDB(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir) / "archive_root"
        self.root_path.mkdir()
        
        self.db_dir = Path(self.test_dir) / "db_dir"
        self.db_dir.mkdir()
        self.external_db_path = self.db_dir / "external.db"
        
        self.source_path = Path(self.test_dir) / "source"
        self.source_path.mkdir()
        self.file1 = self.source_path / "test.txt"
        self.file1.write_text("Hello External DB")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_init_external_db(self):
        cmd_init(self.root_path, db_path_override=self.external_db_path)
        
        # Check DB exists at external location
        self.assertTrue(self.external_db_path.exists())
        
        # Check standard DB location is empty/non-existent
        standard_db = self.root_path / DB_DIR_NAME / "archive.db"
        self.assertFalse(standard_db.exists())

    def test_add_external_db(self):
        cmd_init(self.root_path, db_path_override=self.external_db_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False, db_path_override=self.external_db_path)
        
        # Verify file is in archive root
        self.assertTrue((self.root_path / "docs" / "test.txt").exists())
        
        # Verify entry is in external DB
        conn = sqlite3.connect(self.external_db_path)
        c = conn.cursor()
        c.execute("SELECT path FROM files")
        rows = c.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "docs/test.txt")
        conn.close()

    def test_verify_external_db(self):
        cmd_init(self.root_path, db_path_override=self.external_db_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False, db_path_override=self.external_db_path)
        
        # Should succeed
        try:
            cmd_verify(self.root_path, db_path_override=self.external_db_path)
        except SystemExit:
            self.fail("cmd_verify failed with external DB")

    def test_status_external_db(self):
        cmd_init(self.root_path, db_path_override=self.external_db_path)
        cmd_add(self.root_path, self.file1, "docs", False, False, False, db_path_override=self.external_db_path)
        
        # Just check it runs without error
        cmd_status(self.root_path, db_path_override=self.external_db_path)

    def test_scan_external_db(self):
        cmd_init(self.root_path, db_path_override=self.external_db_path)
        # Manually put a file in archive root
        (self.root_path / "manual.txt").write_text("Manual Content")
        
        # Scan using external DB
        from archiver.commands import cmd_scan
        cmd_scan(self.root_path, db_path_override=self.external_db_path)
        
        # Verify
        conn = sqlite3.connect(self.external_db_path)
        c = conn.cursor()
        c.execute("SELECT path FROM files WHERE path='manual.txt'")
        self.assertTrue(c.fetchone())
        conn.close()

if __name__ == "__main__":
    unittest.main()
