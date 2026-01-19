# TODO list
- [x] never archive .DS_Store files
- [x] dont index dot files in root of archive (can be .spotlight, .fseventd, etc metadata directories)
- [ ] improve performance: explicitly select WAL mode for sqlite: Execute PRAGMA journal_mode=WAL; and PRAGMA synchronous=NORMAL; when connecting.
- [ ] improve performance: add index on path column of files table: CREATE INDEX idx_files_path ON files(path);
- [ ] improve performance: Increase the commit interval in the scan loop from 100 to 10,000 or even 50,000.
- [x] add progress indicator (simply percentage) to the verify command (since we know how many files there are)
- [ ] add some kind of fix command, which given a list of files, adopts the new hash into the db (i.e. we're saying the file on disk is correct). possibly document how to manually fix this (how to calc the hash and update the DB).
- [x] for symlinks, consider their size to always be 0, since it does not matter and the actual size is filesystem dependent.
