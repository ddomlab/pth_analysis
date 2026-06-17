import requests
from . import get_pth
from .config import load_config

def post_pth():
    config = load_config()
    pth_data = get_pth.get_avg_pth(config.serial_port, config.poll_interval_ms)
    try:
        response = requests.post(f"{config.server_url}/store_pth_data", json=pth_data, timeout=10)
        response.raise_for_status()
        print("Data posted successfully:", response.json())
    except requests.exceptions.RequestException as e:
        print("Error posting data:", e)
