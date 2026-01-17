import argparse
import sys
from pathlib import Path
from .commands import cmd_init, cmd_add, cmd_verify, cmd_scan, cmd_status

def main():
    parser = argparse.ArgumentParser(description="Local Archival CLI Tool")
    parser.add_argument("-C", "--directory", type=Path, default=Path.cwd(), help="Directory to operate on (default: current directory)")
    parser.add_argument("-D", "--database", type=Path, default=None, help="Path to database file (default: .archive-index/archive.db inside directory)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # archive init
    parser_init = subparsers.add_parser("init", help="Initialize the archive")

    # archive add
    parser_add = subparsers.add_parser("add", help="Add files to the archive")
    parser_add.add_argument("source", type=Path, help="Source file or directory")
    parser_add.add_argument("dest_subdir", type=str, help="Destination subdirectory within archive")
    parser_add.add_argument("-n", "--non-interactive", action="store_true", help="Skip duplicates automatically (unless overridden)")
    parser_add.add_argument("--accept-duplicates", action="store_true", help="Automatically accept duplicates")
    parser_add.add_argument("--skip-duplicates", action="store_true", help="Automatically skip duplicates")

    # archive verify
    parser_verify = subparsers.add_parser("verify", help="Verify archive integrity")

    # archive scan
    parser_scan = subparsers.add_parser("scan", help="Rebuild database from disk")
    parser_scan.add_argument("-c", "--continue", dest="resume", action="store_true", help="Continue interrupted scan (skip existing files)")

    # archive status
    parser_status = subparsers.add_parser("status", help="Show archive status")

    args = parser.parse_args()
    root_path = args.directory.resolve()
    db_path_override = args.database.resolve() if args.database else None

    try:
        if args.command == "init":
            cmd_init(root_path, db_path_override)
        elif args.command == "add":
            cmd_add(root_path, args.source, args.dest_subdir, args.non_interactive, args.accept_duplicates, args.skip_duplicates, db_path_override)
        elif args.command == "verify":
            cmd_verify(root_path, db_path_override)
        elif args.command == "scan":
            cmd_scan(root_path, args.resume, db_path_override)
        elif args.command == "status":
            cmd_status(root_path, db_path_override)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
