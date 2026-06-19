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


def migrate(csv_path: str, db_path: str, device_id: str) -> tuple[int, int, int]:
    pth_data.init_db(db_path)

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No rows found in {csv_path}; nothing to migrate.")
        return (0, 0, 0)

    before = _row_count(db_path)
    skipped = 0
    for line_no, row in enumerate(rows, start=2):  # 1-indexed rows, +1 for the header line
        row = dict(row)
        row["device_id"] = device_id
        try:
            pth_data.save_reading(db_path, row)
        except (TypeError, ValueError) as e:
            print(f"WARNING: skipping CSV row {line_no} ({row}): {e}")
            skipped += 1
    after = _row_count(db_path)

    return (len(rows), after - before, skipped)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="pth_data.csv")
    parser.add_argument("--db", default="pth_data.db")
    parser.add_argument("--device-id", default=LEGACY_DEVICE_ID)
    args = parser.parse_args()

    csv_rows, new_rows, skipped_rows = migrate(args.csv, args.db, args.device_id)
    print(f"Read {csv_rows} CSV rows.")
    if skipped_rows:
        print(f"Skipped {skipped_rows} row(s) due to errors (see warnings above).")
    print(f"Inserted {new_rows} new reading rows into {args.db} (device_id={args.device_id!r}).")
    print(
        "Note: this may be fewer than (CSV rows x channel count) if some readings were "
        "missing a value for a channel that cycle - those are skipped, not fabricated."
    )
    if new_rows == 0 and csv_rows > 0 and skipped_rows == 0:
        print(
            "WARNING: 0 new rows inserted - this likely means the data was already migrated "
            "(re-run is idempotent), or the CSV has a column/parsing problem. Verify with a spot check."
        )


if __name__ == "__main__":
    main()
