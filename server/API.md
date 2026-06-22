# PTH Server API

All endpoints are served under the `/pth` prefix (the Flask Blueprint's `url_prefix`), regardless of whether `pth_server` is run standalone or mounted inside another Flask app. Examples below assume a base URL like `https://your-server.example.com`.

## Dashboard

### `GET /pth/dashboard`

Serves the browser-based dashboard (`pth_analysis.html`) — a Chart.js time-series view with date-range controls, per-channel toggles, point lookup, and CSV export.

Optionally accepts `start` and `end` query parameters (same flexible epoch-int-or-ISO-8601 format as `/pth/api/range`) as a shortcut straight to a given date range instead of the default last-7-days view:

```
GET /pth/dashboard?start=1740000000&end=1742000000
GET /pth/dashboard?start=2025-02-19T14:30:00&end=2025-03-01T00:00:00
```

Both must be present and parseable to take effect — if either is missing or invalid, the dashboard falls back to its default range. This is handled entirely client-side in the page's JavaScript; the route itself ignores the query string.

## Data ingestion

### `POST /pth/api/store_data`

Stores one reading. Body is a flat JSON object: a `time` field (Unix epoch seconds) plus one numeric field per sensor channel. An optional `device_id` identifies which physical device sent the reading; if omitted, it's stored as `"unknown"`.

**Request body:**
```json
{
  "time": 1750000000,
  "device_id": "greenhouse-1",
  "MS5611 Pressure": 100840.8,
  "SHT31 Temperature": 20.58
}
```

**Response — `200 OK`:**
```json
{ "status": "success" }
```

**Response — `400 Bad Request`** (empty/missing body):
```json
{ "error": "No data provided" }
```

Re-posting an identical `(device_id, channel, time)` triple is a no-op — duplicate inserts are silently ignored rather than erroring or creating a duplicate row.

## Data retrieval

All retrieval endpoints return a JSON array of flat records. Each record has a `time` field (Unix epoch seconds, integer), a `device_id` field, and one field per sensor channel present at that timestamp:

```json
[
  {
    "time": 1750000000,
    "device_id": "greenhouse-1",
    "MS5611 Pressure": 100840.8,
    "SHT31 Temperature": 20.58
  }
]
```

If two devices recorded a reading at the exact same `time`, each produces its own separate record (they are never merged into one row).

Anywhere a timestamp is accepted as a query parameter, it can be given as either a Unix epoch integer (or numeric string) or an ISO 8601 datetime string (e.g. `2025-02-19T14:30:00`).

All three retrieval endpoints below also accept an optional `device_id` to restrict results to one device.

### `GET /pth/api/ndays`

Returns all readings from the past N days.

| Param | Required | Description |
|---|---|---|
| `days` | no (default `1`) | Positive integer number of days to look back from now. |
| `device_id` | no | Restrict to readings from this device only. |

```
GET /pth/api/ndays?days=7
GET /pth/api/ndays?days=7&device_id=greenhouse-1
```

**Response — `400 Bad Request`** if `days` is missing, non-numeric, or ≤ 0:
```json
{ "error": "Invalid days parameter: <value>" }
```

### `GET /pth/api/range`

Returns all readings with `time` between `start` and `end`, inclusive.

| Param | Required | Description |
|---|---|---|
| `start` | yes | Range start — epoch int or ISO 8601 string. |
| `end` | yes | Range end — epoch int or ISO 8601 string. |
| `device_id` | no | Restrict to readings from this device only. |

```
GET /pth/api/range?start=1740000000&end=2025-03-01T00:00:00
GET /pth/api/range?start=1740000000&end=2025-03-01T00:00:00&device_id=greenhouse-1
```

**Response — `400 Bad Request`** if either param is missing or unparseable:
```json
{ "error": "Both start and end are required" }
{ "error": "Invalid start/end value: '<start>', '<end>'" }
```

### `GET /pth/api/closest`

Returns the single reading whose `time` is closest to `time`.

| Param | Required | Description |
|---|---|---|
| `time` | yes | Target timestamp — epoch int or ISO 8601 string. |
| `device_id` | no | Restrict to readings from this device only. |

```
GET /pth/api/closest?time=1740000000
GET /pth/api/closest?time=2025-02-19T14:30:00&device_id=greenhouse-1
```

Unlike the other retrieval endpoints, this returns a single JSON object, not an array:
```json
{
  "time": 1750000000,
  "device_id": "greenhouse-1",
  "MS5611 Pressure": 100840.8,
  "SHT31 Temperature": 20.58
}
```

If multiple devices share the exact closest timestamp and no `device_id` is given, one is returned arbitrarily (whichever was inserted first). Pass `device_id` to get an unambiguous result.

**Response — `400 Bad Request`** if `time` is missing:
```json
{ "error": "No time provided" }
```

**Response — `404 Not Found`** if there is no data at all:
```json
{ "error": "No matching data found" }
```

## Example (Python)

```python
import requests

BASE_URL = "https://your-server.example.com/pth"

response = requests.get(f"{BASE_URL}/api/closest", params={"time": 1740000000})
print(response.json())
## {'MS5611 Pressure': 100840.8, 'SHT31 Relative Humidity': 31.26, 'SHT31 Temperature': 20.58, 'device_id': 'greenhouse-1', 'time': 1762489563}

response = requests.get(f"{BASE_URL}/api/ndays", params={"days": 7})
data = response.json()

response = requests.get(f"{BASE_URL}/api/range", params={"start": 1740000000, "end": "2025-03-01T00:00:00"})
data = response.json()
```

## Migrating from the pre-rename API

| Old route | New route |
|---|---|
| `/pth_analysis` | `/pth/dashboard` |
| `/store_pth_data` | `/pth/api/store_data` |
| `/pth/get_closest` | `/pth/api/closest` |
| `/api/pth/ndays` | `/pth/api/ndays` |
| *(none)* | `/pth/api/range` (new) |
