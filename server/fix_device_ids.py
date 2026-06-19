"""One-time cleanup: unify device_id labeling left inconsistent by a migration mixup.

- Renames every reading labeled --old-name (default "Sensor1") to --new-name
  (default "raspberrypi") - the same physical device, just labeled
  differently before vs. after the sensor's config started using its
  hostname as the device_id.
- Deletes every reading labeled --remove-name (default "legacy") - duplicates
  left behind by a first, failed migration attempt, each of which should
  already have an exact equivalent row under --old-name/--new-name.

Defaults to a dry run that only reports counts - pass --execute to actually
apply the changes. Back up the database first:
    cp pth_data.db pth_data.db.bak-$(date +%Y%m%d)

Usage:
    python3 fix_device_ids.py --db pth_data.db
    python3 fix_device_ids.py --db pth_data.db --execute
"""
import argparse

from pth_server import pth_data


def _count(conn, device_id):
    return conn.execute(
        "SELECT COUNT(*) FROM readings WHERE device_id = ?;", (device_id,)
    ).fetchone()[0]


def _unmatched_count(conn, remove_name, old_name, new_name):
    """ remove_name rows with no exact (channel, time, value) match under old_name/new_name. """
    return conn.execute(
        """
        SELECT COUNT(*) FROM readings r
        WHERE r.device_id = ?
        AND NOT EXISTS (
            SELECT 1 FROM readings o
            WHERE o.channel = r.channel
              AND o.time = r.time
              AND o.value = r.value
              AND o.device_id IN (?, ?)
        );
        """,
        (remove_name, old_name, new_name),
    ).fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default="pth_data.db")
    parser.add_argument("--old-name", default="Sensor1", help="device_id to rename (default: Sensor1)")
    parser.add_argument("--new-name", default="raspberrypi", help="device_id to rename it to (default: raspberrypi)")
    parser.add_argument("--remove-name", default="legacy", help="device_id to delete entirely (default: legacy)")
    parser.add_argument("--execute", action="store_true", help="Actually apply changes (default: dry run only)")
    args = parser.parse_args()

    with pth_data._get_conn(args.db) as conn:
        old_count = _count(conn, args.old_name)
        new_count_before = _count(conn, args.new_name)
        remove_count = _count(conn, args.remove_name)
        unmatched = _unmatched_count(conn, args.remove_name, args.old_name, args.new_name)

        print(f"'{args.old_name}': {old_count} row(s) to rename to '{args.new_name}'")
        print(f"'{args.new_name}': {new_count_before} row(s) already exist under this name")
        print(f"'{args.remove_name}': {remove_count} row(s) to delete")
        if unmatched:
            print(
                f"WARNING: {unmatched} of those '{args.remove_name}' row(s) have NO exact "
                f"(channel, time, value) match under '{args.old_name}' or '{args.new_name}'. "
                f"Deleting them would lose data that isn't actually duplicated elsewhere."
            )
        else:
            print(f"Confirmed: every '{args.remove_name}' row has an exact equivalent under '{args.old_name}'.")

        if not args.execute:
            print("\nDry run only - no changes made. Re-run with --execute to apply.")
            return

        if unmatched:
            print(
                f"\nABORTING: refusing to delete with --execute while {unmatched} unmatched "
                f"'{args.remove_name}' row(s) exist. Investigate them first (see warning above)."
            )
            return

        conn.execute(
            "UPDATE OR IGNORE readings SET device_id = ? WHERE device_id = ?;",
            (args.new_name, args.old_name),
        )
        conn.execute("DELETE FROM readings WHERE device_id = ?;", (args.remove_name,))

        old_count_after = _count(conn, args.old_name)
        new_count_after = _count(conn, args.new_name)
        remove_count_after = _count(conn, args.remove_name)

    renamed = new_count_after - new_count_before
    still_old = old_count_after
    print(f"\nRenamed {renamed} row(s) from '{args.old_name}' to '{args.new_name}'.")
    if still_old:
        print(
            f"WARNING: {still_old} row(s) remain labeled '{args.old_name}' - a '{args.new_name}' "
            f"row already exists at the same (channel, time), so the rename was skipped for those "
            f"to avoid data loss. Investigate manually."
        )
    print(f"Deleted {remove_count - remove_count_after} row(s) labeled '{args.remove_name}'.")


if __name__ == "__main__":
    main()
