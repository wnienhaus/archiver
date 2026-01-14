import unittest
import shutil
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.commands import cmd_init, cmd_add

class TestDuplicateDisplay(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.root_path = Path(self.test_dir)
        self.file1 = Path(tempfile.mkdtemp()) / "file1.txt"
        self.file1.write_text("Content 1")
        
        # Suppress stdout/stderr
        self.suppress_output = patch('sys.stdout', new=StringIO())
        self.suppress_error = patch('sys.stderr', new=StringIO())
        self.suppress_output.start()
        self.suppress_error.start()

    def tearDown(self):
        self.suppress_output.stop()
        self.suppress_error.stop()
        shutil.rmtree(self.test_dir)
        shutil.rmtree(self.file1.parent)

    def test_duplicate_display(self):
        cmd_init(self.root_path)
        
        # Add first copy
        cmd_add(self.root_path, self.file1, "folder1", False, False, False)
        
        # Add second copy (accepted)
        with patch('builtins.input', return_value='y'):
            cmd_add(self.root_path, self.file1, "folder2", False, False, False)
            
        # Add third copy, verify output contains previous 2
        captured_output = StringIO()
        with patch('sys.stdout', captured_output), patch('builtins.input', return_value='n'):
            cmd_add(self.root_path, self.file1, "folder3", False, False, False)
        
        output = captured_output.getvalue()
        self.assertIn("Existing copies:", output)
        self.assertIn("- folder1/file1.txt", output)
        self.assertIn("- folder2/file1.txt", output)

if __name__ == '__main__':
    unittest.main()
