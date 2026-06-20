import requests
import urllib3
import os
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

UDM_IP = os.getenv("UNIFI_IP")
API_KEY = os.getenv("UNIFI_API_KEY")
SITE_ID = "default"

headers = {
    "X-API-KEY": API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Fetch all vouchers from the hotspot
response = requests.get(
    f"{UDM_IP}/proxy/network/api/s/{SITE_ID}/stat/voucher",
    headers=headers,
    verify=False
)

print("Status code:", response.status_code)

data = response.json()
vouchers = data.get("data", [])

if vouchers:
    # Get the most recently created voucher
    latest = sorted(vouchers, key=lambda v: v["create_time"], reverse=True)[0]
    print(f"Latest voucher code: {latest['code']}")
    print(f"Note: {latest.get('note', 'N/A')}")
    print(f"Data limit: {latest.get('qos_usage_quota', 'unlimited')}")
    print(f"Expires after: {latest.get('duration', 'N/A')} minutes")
else:
    print("No vouchers found.")