import os
import shutil
import sys
import time
from pathlib import Path
from datetime import datetime
import sqlite3

from .database import get_db_path, init_db, get_connection, DB_DIR_NAME
from .utils import calculate_file_hash, is_hidden

def cmd_init(root_path: Path):
    """Initializes the archive."""
    # Check for existing hidden files in root
    for item in root_path.iterdir():
        if is_hidden(item) and item.name != DB_DIR_NAME:
            print(f"Error: Hidden entry found in root: {item.name}")
            print("The archive root must not contain hidden files (except .archive-index).")
            sys.exit(1)

    db_path = get_db_path(root_path)
    if db_path.exists():
        print("Archive already initialized.")
    else:
        init_db(db_path)
        print(f"Archive initialized at {root_path}")

def cmd_add(root_path: Path, source: Path, dest_subdir: str, non_interactive: bool, accept_duplicates: bool, skip_duplicates: bool):
    """Adds files to the archive."""
    db_path = get_db_path(root_path)
    if not db_path.exists():
        print("Error: Archive not initialized. Run 'archive init' first.")
        sys.exit(1)

    if dest_subdir.startswith(".") or dest_subdir == DB_DIR_NAME:
        print(f"Error: Destination subdirectory cannot start with '.' or be '{DB_DIR_NAME}'.")
        sys.exit(1)

    dest_dir_abs = root_path / dest_subdir
    # Ensure we are not copying into the DB directory
    if DB_DIR_NAME in dest_dir_abs.parts:
         print(f"Error: Cannot add files to reserved directory {DB_DIR_NAME}")
         sys.exit(1)

    conn = get_connection(db_path)
    cursor = conn.cursor()

    files_to_process = []
    if source.is_file():
        files_to_process.append(source)
    elif source.is_dir():
        for root, _, files in os.walk(source):
            for file in files:
                files_to_process.append(Path(root) / file)
    else:
        print(f"Error: Source {source} does not exist.")
        sys.exit(1)

    for src_file in files_to_process:
        try:
            # 1. Calculate Hash & Size
            file_size = 0 if src_file.is_symlink() else src_file.stat().st_size
            file_hash = calculate_file_hash(src_file)

            # 2. Check for duplicates
            cursor.execute("""
                SELECT f.path 
                FROM files f 
                JOIN hash_index h ON f.id = h.file_id 
                WHERE h.hash=? AND h.size=? 
                LIMIT 11
            """, (file_hash, file_size))
            existing_rows = cursor.fetchall()
            existing_paths = [row[0] for row in existing_rows]
            
            is_duplicate = len(existing_paths) > 0
            should_add = True

            if is_duplicate:
                # Prepare display string for existing copies
                msg_existing = "  Existing copies:\n"
                for p in existing_paths[:10]:
                    msg_existing += f"    - {p}\n"
                if len(existing_paths) > 10:
                    msg_existing += f"    ... and {len(existing_paths) - 10} more.\n"

                if skip_duplicates:
                    print(f"Skipping duplicate: {src_file.name}")
                    print(msg_existing, end="")
                    should_add = False
                elif accept_duplicates:
                    print(f"Adding duplicate: {src_file.name}")
                    print(msg_existing, end="")
                    should_add = True
                elif non_interactive:
                    print(f"Skipping duplicate (non-interactive): {src_file.name}")
                    print(msg_existing, end="")
                    should_add = False
                else:
                    # Prompt
                    print(f"\nDuplicate detected: {src_file}")
                    print(f"Size: {file_size}, Hash: {file_hash}")
                    print(msg_existing, end="")
                    response = input("Add duplicate? (y/N): ").lower()
                    if response == 'y':
                        should_add = True
                    else:
                        should_add = False
            
            if should_add:
                # 3. Determine Destination Path
                # We maintain the structure relative to the source directory if it's a directory add, 
                # or just the filename if it's a file add?
                # Spec says: "Recursively add files"
                # Usually: add /tmp/photos /year/2023 -> /root/year/2023/photos/img.jpg
                # Or: add /tmp/photos/img.jpg /year/2023 -> /root/year/2023/img.jpg
                
                if source.is_dir():
                    rel_path = src_file.relative_to(source)
                    final_dest = dest_dir_abs / rel_path
                else:
                    final_dest = dest_dir_abs / src_file.name

                if final_dest.exists():
                    print(f"Error: Destination file already exists: {final_dest}")
                    print("Skipping to avoid overwrite.")
                    continue
                
                final_dest.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file (preserving symlinks)
                shutil.copy2(src_file, final_dest, follow_symlinks=False)
                
                # Update DB
                # Path stored relative to archive root
                rel_dest_path = final_dest.relative_to(root_path)
                
                cursor.execute(
                    "INSERT INTO files (path, size, hash) VALUES (?, ?, ?)",
                    (str(rel_dest_path), file_size, file_hash)
                )
                file_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO hash_index (hash, size, file_id) VALUES (?, ?, ?)",
                    (file_hash, file_size, file_id)
                )
                conn.commit()
                print(f"Added: {rel_dest_path}")

        except Exception as e:
            print(f"Error processing {src_file}: {e}")
            # Continue on per-file errors as per spec
            continue

    conn.close()

def cmd_verify(root_path: Path):
    """Verifies the integrity of archived files."""
    db_path = get_db_path(root_path)
    if not db_path.exists():
        print("Error: Archive not initialized.")
        sys.exit(1)

    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, path, size, hash FROM files")
    files = cursor.fetchall()
    
    print(f"Verifying {len(files)} files...")
    
    issues = 0
    for file_id, rel_path_str, expected_size, expected_hash in files:
        file_path = root_path / rel_path_str
        
        if not file_path.exists() and not file_path.is_symlink():
            print(f"MISSING: {rel_path_str}")
            issues += 1
            continue
            
        current_size = 0 if file_path.is_symlink() else file_path.stat().st_size

        if current_size != expected_size:
            print(f"CORRUPTED (Size mismatch): {rel_path_str}")
            issues += 1
            continue
            
        current_hash = calculate_file_hash(file_path)
        if current_hash != expected_hash:
            print(f"CORRUPTED (Hash mismatch): {rel_path_str}")
            issues += 1
            continue
            
        # Update last_verified
        #cursor.execute("UPDATE files SET last_verified = CURRENT_TIMESTAMP WHERE id = ?", (file_id,))
        # Commit periodically or at end? SQLite is fast enough for batch commit at end for this tool size probably,
        # but let's commit every file or batch to be safe against interruption?
        # Let's commit at the end for performance.
    
    conn.commit()
    conn.close()
    
    if issues == 0:
        print("Verification complete: All files OK.")
    else:
        print(f"Verification complete: {issues} issues found.")

def cmd_scan(root_path: Path, resume: bool = False):
    """Rebuilds the database from disk."""
    db_path = get_db_path(root_path)
    
    existing_paths = set()

    if db_path.exists():
        conn = get_connection(db_path)
        cursor = conn.cursor()

        if not resume:
            cursor.execute("SELECT count(*) FROM files")
            if cursor.fetchone()[0] > 0:
                print("Error: Database already contains data. Use --continue to resume or delete the database to restart.")
                conn.close()
                sys.exit(1)

        if resume:
            print("Resuming database scan...")
            cursor.execute("SELECT path FROM files")
            # Load all existing paths into a set for O(1) lookup
            existing_paths = {row[0] for row in cursor.fetchall()}
            print(f"Found {len(existing_paths)} existing entries in database.")
        else:
            print("Rebuilding database...")
            cursor.execute("DELETE FROM hash_index")
            cursor.execute("DELETE FROM files")
            cursor.execute("DELETE FROM sqlite_sequence") # Reset autoincrement
            conn.commit()
    else:
        init_db(db_path)
        conn = get_connection(db_path)
        cursor = conn.cursor()

    count = 0
    skipped_count = 0
    # Walk archive excluding .archive-index
    for root, dirs, files in os.walk(root_path):
        # Modify dirs in-place to skip .archive-index
        if DB_DIR_NAME in dirs:
            dirs.remove(DB_DIR_NAME)
        
        for file in files:
            file_path = Path(root) / file
            # "Include hidden files below root" -> so we don't skip hidden files here.
            
            try:
                rel_path = file_path.relative_to(root_path)
                rel_path_str = str(rel_path)

                if resume and rel_path_str in existing_paths:
                    skipped_count += 1
                    continue

                size = 0 if file_path.is_symlink() else file_path.stat().st_size

                file_hash = calculate_file_hash(file_path)
                
                cursor.execute(
                    "INSERT INTO files (path, size, hash) VALUES (?, ?, ?)",
                    (rel_path_str, size, file_hash)
                )
                file_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO hash_index (hash, size, file_id) VALUES (?, ?, ?)",
                    (file_hash, size, file_id)
                )
                count += 1
                if count % 100 == 0:
                    print(f"Scanned {count} files...", end="\r")
                    conn.commit()
            except Exception as e:
                print(f"Error scanning {file_path}: {e}")

    conn.commit()
    conn.close()
    if resume:
        print(f"\nScan complete. Added {count} new files (Skipped {skipped_count} existing).")
    else:
        print(f"\nScan complete. Indexed {count} files.")

def cmd_status(root_path: Path):
    """Displays archive status."""
    db_path = get_db_path(root_path)
    if not db_path.exists():
        print("Archive not initialized.")
        return

    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*), SUM(size) FROM files")
    file_count, total_size = cursor.fetchone()
    if total_size is None: total_size = 0
    
    cursor.execute("SELECT COUNT(*) FROM (SELECT hash, size FROM hash_index GROUP BY hash, size HAVING COUNT(*) > 1)")
    duplicate_groups = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM files WHERE last_verified IS NULL")
    never_verified = cursor.fetchone()[0]
    
    print(f"Archive Status for {root_path}")
    print(f"--------------------------------")
    print(f"Total Files: {file_count}")
    print(f"Total Size:  {total_size} bytes")
    print(f"Duplicate Groups: {duplicate_groups}")
    print(f"Unverified Files: {never_verified}")
    
    conn.close()
