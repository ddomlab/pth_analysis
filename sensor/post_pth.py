import requests
import get_pth

URL = 'https://...'

def post_pth():
    pth_data = get_pth.get_avg_pth()
    try:
        response = requests.post(f"{URL}/store_pth_data", json=pth_data, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes
        print("Data posted successfully:", response.json())
    except requests.exceptions.RequestException as e:
        print("Error posting data:", e)
if __name__ == "__main__":
    post_pth()