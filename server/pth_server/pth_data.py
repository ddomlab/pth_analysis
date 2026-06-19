import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

DB_TIMEOUT_S = 5.0


@contextmanager
def _get_conn(db_path: str):
    conn = sqlite3.connect(db_path, timeout=DB_TIMEOUT_S)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """ Idempotent schema creation. Call once at app startup. """
    with _get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT    NOT NULL,
                channel   TEXT    NOT NULL,
                value     REAL    NOT NULL,
                time      INTEGER NOT NULL,
                UNIQUE (device_id, channel, time) ON CONFLICT IGNORE
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_time ON readings (time);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_device_time ON readings (device_id, time);")


def save_reading(db_path: str, data: dict) -> bool:
    """ Insert one reading. `data` is the flat dict from the sensor POST:
    {"time": <epoch int>, "device_id": <str, optional>, <channel>: <float>, ...} """
    data = dict(data)
    time_val = int(data.pop("time"))
    device_id = str(data.pop("device_id", "unknown"))
    # None/empty means "this channel wasn't recorded this cycle" (e.g. the old
    # flat-CSV format could write a short row if a channel dropped out, which
    # csv.DictReader then reads back as None) - skip it rather than inserting
    # a fabricated value.
    rows = [
        (device_id, channel, float(value), time_val)
        for channel, value in data.items()
        if value is not None and value != ""
    ]
    with _get_conn(db_path) as conn:
        conn.executemany(
            "INSERT INTO readings (device_id, channel, value, time) VALUES (?, ?, ?, ?);",
            rows,
        )
    return True


def _parse_time(value: str | int) -> int:
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        return int(datetime.fromisoformat(value).timestamp())
    return int(value)


def _pivot_to_records(rows: list[sqlite3.Row]) -> list[dict]:
    """ Group narrow (device_id, channel, value, time) rows into wide flat dicts
    keyed by (time, device_id), matching the original CSV-era JSON shape plus
    an additive 'device_id' field. """
    grouped: dict[tuple[int, str], dict] = {}
    for row in rows:
        key = (row["time"], row["device_id"])
        record = grouped.setdefault(key, {"time": row["time"], "device_id": row["device_id"]})
        record[row["channel"]] = row["value"]
    return list(grouped.values())


def get_recent_readings(db_path: str, days: float, device_id: str | None = None) -> list[dict]:
    """ Get readings from the last 'days' days, optionally restricted to one device_id. """
    cutoff_time = int((datetime.now() - pd.Timedelta(days=days)).timestamp())
    query = "SELECT device_id, channel, value, time FROM readings WHERE time >= ?"
    params: list = [cutoff_time]
    if device_id:
        query += " AND device_id = ?"
        params.append(device_id)
    query += " ORDER BY time;"
    with _get_conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return _pivot_to_records(rows)


def get_readings_in_range(
    db_path: str, start: str | int, end: str | int, device_id: str | None = None
) -> list[dict]:
    """ Get readings with time in [start, end], inclusive, optionally restricted to one
    device_id. Each bound accepts a Unix epoch integer (or numeric string) or an ISO 8601
    datetime string.

    Returns a plain list of dicts rather than a DataFrame deliberately: when
    devices report different channel sets, building a DataFrame from these
    records pads each row out to the union of all columns, filling the gaps
    with NaN - which Flask's jsonify then emits as a bare `NaN` token. That's
    not valid JSON, so browsers' JSON.parse (and fetch().json()) reject it. """
    start_time = _parse_time(start)
    end_time = _parse_time(end)
    query = "SELECT device_id, channel, value, time FROM readings WHERE time >= ? AND time <= ?"
    params: list = [start_time, end_time]
    if device_id:
        query += " AND device_id = ?"
        params.append(device_id)
    query += " ORDER BY time;"
    with _get_conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return _pivot_to_records(rows)


def get_closest_reading(db_path: str, target_time: str | int, device_id: str | None = None) -> dict | None:
    """ Get the reading with the closest time to the target_time, optionally restricted to
    one device_id. Without a device_id, if multiple devices share the exact closest
    timestamp, one is returned arbitrarily - passing device_id makes the result unambiguous. """
    target_time = _parse_time(target_time)

    closest_query = "SELECT time FROM readings"
    closest_params: list = []
    if device_id:
        closest_query += " WHERE device_id = ?"
        closest_params.append(device_id)
    closest_query += " ORDER BY ABS(time - ?) LIMIT 1;"
    closest_params.append(target_time)

    with _get_conn(db_path) as conn:
        closest_row = conn.execute(closest_query, closest_params).fetchone()
        if closest_row is None:
            return None

        rows_query = "SELECT device_id, channel, value, time FROM readings WHERE time = ?"
        rows_params: list = [closest_row["time"]]
        if device_id:
            rows_query += " AND device_id = ?"
            rows_params.append(device_id)

        rows = conn.execute(rows_query, rows_params).fetchall()

    records = _pivot_to_records(rows)
    return records[0] if records else None
