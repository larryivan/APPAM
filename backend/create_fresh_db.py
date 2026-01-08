#!/usr/bin/env python3
"""
Create a brand-new SQLite database for APPAM.

This script creates the projects and process_history tables without
any password-related columns.
"""

import argparse
import os
import sqlite3
import sys


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    creator TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    command TEXT,
    status TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration REAL,
    exit_code INTEGER,
    error_message TEXT,
    logs TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);
"""


def create_db(db_path: str, force: bool) -> None:
    if os.path.exists(db_path):
        if not force:
            raise FileExistsError(
                f"Database already exists at {db_path}. Use --force to overwrite."
            )
        os.remove(db_path)

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def main() -> int:
    default_path = os.path.join(os.path.dirname(__file__), "app_database.db")

    parser = argparse.ArgumentParser(
        description="Create a fresh APPAM SQLite database."
    )
    parser.add_argument(
        "--path",
        default=default_path,
        help=f"Database file path (default: {default_path})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database if it exists.",
    )
    args = parser.parse_args()

    try:
        create_db(args.path, args.force)
        print(f"Created new database at: {args.path}")
        return 0
    except Exception as exc:
        print(f"Failed to create database: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
