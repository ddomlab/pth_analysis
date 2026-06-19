# Automatic Tracking of Pressure, Temperature, and Humidity Data
**Data Driven Organic Materials Lab**

## Materials
- Dracal VCP-PTH200 (https://www.dracal.com/en/product/pth200/)
- Raspberry Pi
- DigitalOcean Droplet running Flask Server

## Workflow

<img width="715" height="691" alt="image" src="https://github.com/user-attachments/assets/eb1e824b-68ff-4ea9-8e0b-444fba09f5de" />

The PTH monitoring system is composed of two major components: the sensor assembly and the server. The sensor assembly, a Raspberry Pi connected to the VCP-PTH200, posts HTTP requests to the server on a fixed schedule (in our case, every 15 minutes) containing pressure, temperature, and humidity readings.

The Flask server, hosted on a DigitalOcean Droplet, exposes several endpoints for data ingestion and retrieval, all under a `/pth` prefix. It's a Flask Blueprint, distributed as a pip-installable package (`server/`) — it can run as its own standalone server (`server/app.py`) or be mounted into an existing Flask application. Incoming PTH data is accepted at `/pth/api/store_data` and stored in a SQLite database, tagged with the identifier of the device that sent it.

A browser-based dashboard is served at `/pth/dashboard` on the same DigitalOcean Droplet. The interface is built in vanilla HTML, CSS, and JavaScript, using Chart.js for visualization. On load, it fetches the past 7 days of data from `/pth/api/ndays` and renders a time-series line plot. Each sensor channel (pressure, temperature, humidity) is assigned its own Y-axis, allowing channels with disparate units and scales to be displayed simultaneously without compression.

The interface exposes several controls: the displayed date range can be narrowed using start and end datetime pickers, individual sensor channels can be toggled on or off via a checkbox panel, and a point lookup tool queries `/pth/api/closest` to retrieve the recorded values nearest to a user-specified timestamp. A statistics panel below the chart displays the minimum, maximum, mean, and total point count for each active channel over the selected time window. Data for the current view can also be exported as a CSV file directly from the browser.

<img width="1157" height="1160" alt="image" src="https://github.com/user-attachments/assets/4434c34b-0c72-431a-8d18-1a43940a24b7" />


Data can be retrieved through the API in three ways: `/pth/api/ndays` returns all records from the past N days, `/pth/api/range` returns all records between two given timestamps, and `/pth/api/closest` accepts a Unix timestamp or ISO 8601 datetime string and returns the record with the nearest matching timestamp. All three accept Unix epoch integers or ISO 8601 datetime strings wherever a timestamp is expected. Full endpoint reference: [`server/API.md`](server/API.md).
```python
import requests

BASE_URL = "https://.../pth"

# Unix epoch integer
response = requests.get(f"{BASE_URL}/api/closest", params={"time": 1740000000})
print(response.json())
## {'MS5611 Pressure': 100840.8, 'SHT31 Relative Humidity': 31.26, 'SHT31 Temperature': 20.58, 'device_id': 'greenhouse-1', 'time': 1762489563}

# ISO 8601 datetime string
response = requests.get(f"{BASE_URL}/api/closest", params={"time": "2025-02-19T14:30:00"})
print(response.json())

# Get the last N days of data
response = requests.get(f"{BASE_URL}/api/ndays", params={"days": 7})
data = response.json()  # Returns a list of dicts, one per recorded interval

# Get all data between two timestamps
response = requests.get(f"{BASE_URL}/api/range", params={"start": 1740000000, "end": "2025-03-01T00:00:00"})
data = response.json()
```

## Installation

### Sensor Setup

The sensor installation script creates a systemd service that takes a reading at a fixed interval (default 15 minutes) and posts it to the server.

In the terminal on your sensor device (Raspberry Pi), follow the instructions at [`sensor/INSTALL.md`](sensor/INSTALL.md) to install and configure the sensor.


### Server Setup

On your server, clone this repository. To download only the server code (not the sensor code), run:

```bash
git clone --no-checkout https://github.com/ddomlab/pth_analysis.git && cd pth_analysis
```
```bash
git sparse-checkout init --cone && git sparse-checkout set server && git checkout main
```
Then, pip install the server blueprint

```bash
pip install ./server
```

The server is a pip-installable Flask Blueprint (`pth_server`), usable two ways:

- **As a standalone server** Simply run the provided `server/app.py` (`python3 app.py`, for testing or for production, `gunicorn app:app`). This registers the blueprint on its own dedicated Flask app. See [this guide](https://dev.to/tkirwa/create-a-systemd-service-script-for-running-gunicorn-to-serve-your-application-5aea) for help setting up Gunicorn.
- **Mounted on an existing Flask app**: In your app's setup code:
  ```python
  import pth_server 

  app.register_blueprint(pth_server.pth_bp)
  pth_server.init_app_db(app)
  ```

Either way, every PTH route lives under the `/pth` prefix (`/pth/dashboard`, `/pth/api/...`). Set `app.config["PTH_DB_PATH"]` to control where the SQLite database file is created (defaults to `pth_data.db` in the working directory).

If you're migrating an existing flat `pth_data.csv` from an older version of this project, see `server/migrate_csv_to_db.py`.
