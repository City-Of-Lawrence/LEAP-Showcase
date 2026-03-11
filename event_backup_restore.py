#!/usr/bin/env python3
"""
Backup and restore the SQLite tables `events` and `event_wards`
to/from an Excel workbook.

Usage:
    python event_backup_restore.py -b   # backup DB -> Excel
    python event_backup_restore.py -r   # restore Excel -> DB

Assumptions:
- Script, SQLite DB, and Excel workbook are in the same directory
- DB file name: upinmgmt.sqlite
- Workbook file name: event_ackup_and_restore.xlsx
- Excel sheet names: Events, event_wards
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openpyxl import Workbook, load_workbook


DB_NAME = "upinmgmt.sqlite"
XLSX_NAME = "event_ackup_and_restore.xlsx"

# Map DB table name -> Excel sheet name
TABLE_SHEET_MAP = {
    "events": "Events",
    "event_wards": "event_wards",
}


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent


def get_db_path() -> Path:
    return get_base_dir() / DB_NAME


def get_xlsx_path() -> Path:
    return get_base_dir() / XLSX_NAME


def connect_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not rows:
        raise ValueError(f"Table not found or has no schema info: {table_name}")
    return [row["name"] for row in rows]


def fetch_table_data(
    conn: sqlite3.Connection, table_name: str, columns: List[str]
) -> List[Tuple[Any, ...]]:
    col_list = ", ".join(f'"{c}"' for c in columns)
    query = f'SELECT {col_list} FROM "{table_name}"'
    return conn.execute(query).fetchall()


def normalize_excel_value(value: Any) -> Any:
    """
    Convert Excel cell values to something SQLite can store sensibly.
    Empty strings stay as empty strings; blank cells become None.
    """
    return value


def backup_to_excel(db_path: Path, xlsx_path: Path) -> None:
    conn = connect_db(db_path)
    try:
        if xlsx_path.exists():
            xlsx_path.unlink()

        wb = Workbook()

        # Remove default sheet
        default_sheet = wb.active
        wb.remove(default_sheet)

        for table_name, sheet_name in TABLE_SHEET_MAP.items():
            columns = get_table_columns(conn, table_name)
            rows = fetch_table_data(conn, table_name, columns)

            ws = wb.create_sheet(title=sheet_name)
            ws.append(columns)

            for row in rows:
                ws.append(list(row))

        wb.save(xlsx_path)
        print(f"Backup created: {xlsx_path}")

    finally:
        conn.close()


def read_sheet_rows(ws) -> Tuple[List[str], List[List[Any]]]:
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        raise ValueError(f"Sheet '{ws.title}' is empty.")

    header = list(all_rows[0])
    if any(h is None for h in header):
        raise ValueError(f"Sheet '{ws.title}' has blank column names in the header row.")

    data_rows = [list(r) for r in all_rows[1:]]

    # Remove completely blank trailing rows
    cleaned_rows = []
    for row in data_rows:
        if row is None:
            continue
        if all(cell is None for cell in row):
            continue
        cleaned_rows.append(row)

    return [str(h) for h in header], cleaned_rows


def clear_tables(conn: sqlite3.Connection) -> None:
    # Delete child first, then parent
    conn.execute('DELETE FROM "event_wards"')
    conn.execute('DELETE FROM "events"')


def insert_rows(
    conn: sqlite3.Connection,
    table_name: str,
    expected_columns: List[str],
    sheet_columns: List[str],
    rows: List[List[Any]],
) -> None:
    if sheet_columns != expected_columns:
        raise ValueError(
            f"Column mismatch for table '{table_name}'.\n"
            f"Expected: {expected_columns}\n"
            f"Found in sheet: {sheet_columns}"
        )

    placeholders = ", ".join("?" for _ in expected_columns)
    col_list = ", ".join(f'"{c}"' for c in expected_columns)
    sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'

    normalized_rows = []
    expected_len = len(expected_columns)

    for idx, row in enumerate(rows, start=2):  # Excel row numbering starts at 1; data starts at row 2
        if len(row) < expected_len:
            row = row + [None] * (expected_len - len(row))
        elif len(row) > expected_len:
            row = row[:expected_len]

        normalized = [normalize_excel_value(v) for v in row]
        normalized_rows.append(normalized)

    if normalized_rows:
        conn.executemany(sql, normalized_rows)


def restore_from_excel(db_path: Path, xlsx_path: Path) -> None:
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Workbook not found: {xlsx_path}")

    conn = connect_db(db_path)
    try:
        wb = load_workbook(xlsx_path, data_only=True)

        required_sheets = set(TABLE_SHEET_MAP.values())
        missing = [s for s in required_sheets if s not in wb.sheetnames]
        if missing:
            raise ValueError(f"Workbook is missing required sheet(s): {missing}")

        with conn:
            clear_tables(conn)

            # Restore parent first, then child
            restore_order = ["events", "event_wards"]

            for table_name in restore_order:
                sheet_name = TABLE_SHEET_MAP[table_name]
                ws = wb[sheet_name]

                expected_columns = get_table_columns(conn, table_name)
                sheet_columns, rows = read_sheet_rows(ws)

                insert_rows(
                    conn=conn,
                    table_name=table_name,
                    expected_columns=expected_columns,
                    sheet_columns=sheet_columns,
                    rows=rows,
                )

        print(f"Restore completed from: {xlsx_path}")

    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backup/restore events and event_wards between SQLite and Excel."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help="Backup DB tables to Excel workbook",
    )
    group.add_argument(
        "-r",
        "--restore",
        action="store_true",
        help="Restore DB tables from Excel workbook",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = get_db_path()
    xlsx_path = get_xlsx_path()

    try:
        if args.backup:
            backup_to_excel(db_path, xlsx_path)
        elif args.restore:
            restore_from_excel(db_path, xlsx_path)
        else:
            raise ValueError("No valid operation selected.")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())