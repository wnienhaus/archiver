# Local Archiver CLI Tool

## Project Overview

This project is a local archival CLI tool implemented in Python. It is designed to be an append-only archive manager that stores files in a human-readable directory tree while maintaining a SQLite index of file hashes.

**Key Goals:**
*   **Data Integrity:** Uses SHA-256 hashing to verify file content.
*   **Duplicate Detection:** Prevents accidental duplicates by hashing content before addition.
*   **Safety:** strictly append-only; never modifies, deletes, renames, or overwrites archived files.
*   **Rebuildable:** The database can be fully reconstructed from the disk content.

## Architecture

*   **Language:** Python 3.11+
*   **Database:** SQLite (stored in `.archive-index/archive.db`)
*   **Entry Point:** `archive` script (wraps `archiver.main`).

### Directory Structure

*   `archiver/`: Main source package.
    *   `main.py`: CLI entry point, argument parsing.
    *   `commands.py`: Core logic for commands (`init`, `add`, `verify`, `scan`, `status`).
    *   `database.py`: Database connection and schema definitions.
    *   `utils.py`: Utility functions (hashing, file checks).
*   `tests/`: Unit and integration tests.
*   `.archive-index/`: Hidden directory containing the SQLite database (created upon initialization).

## Building and Running

### Prerequisites
*   Python 3.11 or higher.

### Installation
No installation is required. The tool can be run directly via the wrapper script.

### Usage
Run the tool using the `./archive` script.

**Common Commands:**

*   **Initialize an archive:**
    ```bash
    ./archive init
    # Or in a specific directory:
    ./archive -C /path/to/archive init
    ```

*   **Add files:**
    ```bash
    ./archive add <source_path> <dest_subdir>
    # Flags:
    #   -n / --non-interactive: Skip duplicates automatically.
    #   --accept-duplicates: Automatically add duplicates.
    #   --skip-duplicates: Automatically skip duplicates.
    ```

*   **Verify Integrity:**
    ```bash
    ./archive verify
    ```

*   **Check Status:**
    ```bash
    ./archive status
    ```

*   **Rebuild Database:**
    ```bash
    ./archive scan
    # Resume an interrupted scan:
    ./archive scan --continue
    ```

## Development Conventions

### Testing
Tests are written using the `unittest` framework.

*   **Run all tests:**
    ```bash
    python3 -m unittest discover tests
    ```

### Continuous Integration
A GitHub Actions workflow is defined in `.github/workflows/test.yml` to run tests on every push for Python 3.11 and 3.12 (and potentially newer versions like 3.14 as seen in the config).

### Database Schema
The SQLite database consists of two main tables:
1.  `files`: Stores file metadata (id, path, size, hash, timestamps).
2.  `hash_index`: Lookup table for duplicate detection (hash, size, file_id).

### Code Style
*   Follows standard Python conventions.
*   Modules are designed to be small and explicit.
*   Strict adherence to "fail fast" on structural violations and "continue" on per-file errors.
