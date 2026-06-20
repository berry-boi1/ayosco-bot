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

# Test: create one voucher — 300MB limit, valid for 24 hours, single use
payload = {
    "count": 1,           # how many vouchers to generate
    "expire": 1440,       # validity in minutes (1440 = 24 hours)
    "expire_number": 1,
    "expire_unit": 1440,
    "quota": 1,           # 1 = single use
    "note": "ayosco_test_300mb",
    "up": None,           # upload limit (None = unlimited)
    "down": None,         # download limit (None = unlimited)
    "bytes": 307200       # data limit in MB (300MB = 300 * 1024 = 307200 KB)
}

response = requests.post(
    f"{UDM_IP}/proxy/network/api/s/{SITE_ID}/cmd/hotspot",
    headers=headers,
    json={**payload, "cmd": "create-voucher"},
    verify=False
)

print("Status code:", response.status_code)
print("Response:", response.text)
