#!/usr/bin/env python3
"""
Create a fresh APPAM SQLite database using the canonical application schema.
"""

import argparse
import importlib.util
import os
import sys


def create_db(db_path: str, force: bool) -> None:
    if os.path.exists(db_path):
        if not force:
            raise FileExistsError(
                f"Database already exists at {db_path}. Use --force to overwrite."
            )
        os.remove(db_path)

    os.makedirs(os.path.dirname(os.path.abspath(db_path)) or ".", exist_ok=True)
    os.environ["APPAM_DB_PATH"] = db_path

    database_path = os.path.join(os.path.dirname(__file__), "app", "database.py")
    spec = importlib.util.spec_from_file_location("appam_database", database_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load database module from {database_path}")
    database_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database_module)

    database_module.init_db()


def main() -> int:
    default_path = os.path.join(os.path.dirname(__file__), "app_database.db")

    parser = argparse.ArgumentParser(
        description="Create a fresh APPAM SQLite database with the current schema."
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
