# Personal Archiver

A simple, append-only file archiver designed for efficient personal archive management. It stores files in a human-readable directory structure and maintains a SQLite index to ensure you never back up the same file twice (unless you want to). A verification option allows testing occasionally that data on the archive disk is still readable and still matches the original content.

This tool is meant for maintaining an archive NOT a backup. The archive itself can then be backed up as necessary.

## Key Features

*   **Data Integrity:** Uses SHA-256 hashing to verify file content.
*   **Duplicate Detection:** Prevents redundant copies by hashing content before adding.
*   **Safety:** Strictly append-only; never modifies, deletes, or overwrites archived files.
*   **Portable:** The index can be fully reconstructed from the files on disk.

## Getting Started

### Prerequisites

*   Python 3.11 or higher.

### Usage

The tool is run via the `./archive` script.

1.  **Initialize an archive:**
    ```bash
    ./archive init
    ```
2.  **Add files or directories:**
    ```bash
    ./archive add /path/to/source photos/2023
    ```
3.  **Verify your archive:**
    ```bash
    ./archive verify
    ```

## Command Reference

### Global Options
*   `-C <path>`: Specify the archive root directory (default: current directory).
*   `-D <path>`: Specify an external location for the database file.

### Commands
*   `init`: Prepares the current directory to be an archive.
*   `add <source> <dest>`: Recursively adds files from `source` into the specified `dest` folder within the archive.
    *   `--skip-duplicates`: Automatically skip files already in the archive.
    *   `--accept-duplicates`: Automatically add files even if they are duplicates.
    *   `-n`: Non-interactive mode (skips duplicates by default).
*   `verify`: Checks every file in the archive against its recorded hash to ensure no corruption or missing data.
*   `status`: Shows the total number of files, storage size, and duplicate statistics.
*   `scan`: Rebuilds the database index by scanning the files on disk.
    *   `--continue`: Resumes an interrupted scan.

## Good to Know

*   **Hidden Files:** Hidden files and directories (starting with `.`) are ignored if they are in the root of the archive to keep the top level clean. They are preserved if they are inside subdirectories.
*   **System Files:** `.DS_Store` files are automatically ignored and never archived.
*   **Symbolic Links:** Symlinks are preserved as links and are not followed (the content they point to is not copied). If a link points to a location outside the archive, it may be broken when accessing it from within the archive.