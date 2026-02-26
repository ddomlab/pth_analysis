# Automatic Tracking of Pressure, Temperature, and Humidity Data
**Data Driven Organic Materials Lab**

## Materials
- Dracal VCP-PTH200 (https://www.dracal.com/en/product/pth200/)
- Raspberry Pi
- DigitalOcean Droplet running Flask Server (optional)

## Workflow
<img width="715" height="691" alt="image" src="https://gist.github.com/user-attachments/assets/8d86f329-451f-465d-9548-6e8c920ec92b" />

The PTH monitoring system is composed of two major components: the sensor assembly and the server. The sensor assembly, a Raspberry Pi connected to the VCP-PTH200, posts HTTP requests to the server on a fixed schedule (in our case, every 15 minutes) containing pressure, temperature, and humidity readings.

The Flask server, hosted on a DigitalOcean Droplet, exposes several endpoints for data ingestion and retrieval. Incoming PTH data is accepted at `/store_pth_data` and appended as a row to a CSV file, with headers written automatically on first use. The CSV stores each record as a flat dictionary keyed by sensor channel name (e.g., Temperature, Pressure, Humidity) alongside a Unix epoch timestamp.

A browser-based dashboard is served at `/pth_analysis` on the same DigitalOcean Droplet. The interface is built in vanilla HTML, CSS, and JavaScript, using Chart.js for visualization. On load, it fetches the past 7 days of data from `/api/pth/ndays` and renders a time-series line plot. Each sensor channel (pressure, temperature, humidity) is assigned its own Y-axis, allowing channels with disparate units and scales to be displayed simultaneously without compression.

The interface exposes several controls: the displayed date range can be narrowed using start and end datetime pickers, individual sensor channels can be toggled on or off via a checkbox panel, and a point lookup tool queries `/pth/get_closest` to retrieve the recorded values nearest to a user-specified timestamp. A statistics panel below the chart displays the minimum, maximum, mean, and total point count for each active channel over the selected time window. Data for the current view can also be exported as a CSV file directly from the browser.

<img width="1157" height="1160" alt="image" src="https://gist.github.com/user-attachments/assets/1cdac5e8-49a5-488e-b532-92dbc8a9f217" />


Data can be retrieved through the API in two ways: the `/api/pth/ndays` endpoint returns all records from the past N days as a JSON array, and the `/pth/get_closest` endpoint accepts a Unix timestamp or ISO 8601 datetime string and returns the record with the nearest matching timestamp.
```python
import requests

BASE_URL = "https://..."

# Unix epoch integer
response = requests.get(f"{BASE_URL}/pth/get_closest", params={"time": 1740000000})
print(response.json())
## {'MS5611 Pressure': '100840.8', 'SHT31 Relative Humidity': '31.26', 'SHT31 Temperature': '20.58', 'time': 1762489563}

# ISO 8601 datetime string
response = requests.get(f"{BASE_URL}/pth/get_closest", params={"time": "2025-02-19T14:30:00"})
print(response.json())

# Get the last N days of data
response = requests.get(f"{BASE_URL}/api/pth/ndays", params={"days": 7})
data = response.json()  # Returns a list of dicts, one per recorded interval
```

## Installation

Right now, the code is not quite "distribution-ready," so if you would like to set up a similar system, it may take some work. A simple installation script/process is in the works.

### Sensor Setup

On the Raspberry Pi, only two scripts are used, both of which are in the `sensor/` folder of this repository. Download both of these scripts, and ensure that you have a Python file with the packages listed in `sensor/requirements.txt`. 

The script is executed every 15 minutes through a cron job. To add the cron job, run `crontab -e` and add the following line:

`*/15 * * * * /PATH/TO/PYTHON/ENV/bin/python /PATH/TO/SCRIPT/post_pth.py`

This will run the script every 15 minutes.

### Server Setup

Ensure that you have Flask, Pandas, and Gunicorn installed, and that all files in `server/` and `server/static` are downloaded into the appropriate folder on your server.

In our setup, we had a pre-existing Flask server running, to which we added the endpoints listed in `server/app.py` You can run the provided `app.py` as a new server, or copy the endpoints to an existing server. For production applications, use Gunicorn, rather than the built-in Flask development server.
