import hashlib
from pathlib import Path

# 4MB buffer size
BUFFER_SIZE = 4 * 1024 * 1024

def calculate_file_hash(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file using a 4MB buffer."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(BUFFER_SIZE), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_hidden(path: Path) -> bool:
    """Checks if a file or directory is hidden (starts with .)."""
    return path.name.startswith(".")
