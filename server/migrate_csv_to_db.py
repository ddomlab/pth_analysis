"""One-time migration: import an existing flat pth_data.csv into the new
SQLite readings table. Safe to re-run (inserts are idempotent via the
table's UNIQUE constraint) but intended to be run once.

Usage:
    python3 migrate_csv_to_db.py [--csv pth_data.csv] [--db pth_data.db] [--device-id legacy]
"""
import argparse
import csv

from pth_server import pth_data

LEGACY_DEVICE_ID = "legacy"


def _row_count(db_path: str) -> int:
    with pth_data._get_conn(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM readings;").fetchone()[0]


def migrate(csv_path: str, db_path: str, device_id: str) -> tuple[int, int]:
    pth_data.init_db(db_path)

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No rows found in {csv_path}; nothing to migrate.")
        return (0, 0)

    before = _row_count(db_path)
    for row in rows:
        row = dict(row)
        row["device_id"] = device_id
        pth_data.save_reading(db_path, row)
    after = _row_count(db_path)

    return (len(rows), after - before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="pth_data.csv")
    parser.add_argument("--db", default="pth_data.db")
    parser.add_argument("--device-id", default=LEGACY_DEVICE_ID)
    args = parser.parse_args()

    csv_rows, new_rows = migrate(args.csv, args.db, args.device_id)
    print(f"Read {csv_rows} CSV rows.")
    print(f"Inserted {new_rows} new reading rows into {args.db} (device_id={args.device_id!r}).")
    if new_rows == 0 and csv_rows > 0:
        print(
            "WARNING: 0 new rows inserted - this likely means the data was already migrated "
            "(re-run is idempotent), or the CSV has a column/parsing problem. Verify with a spot check."
        )


if __name__ == "__main__":
    main()
