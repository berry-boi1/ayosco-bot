import requests
import urllib3
import os
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

UDM_IP = os.getenv("UNIFI_IP")
API_KEY = os.getenv("UNIFI_API_KEY")
SITE_ID = "default"

HEADERS = {
    "X-API-KEY": API_KEY,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Maps plan data size to MB — UniFi's "bytes" quota field expects MB, not KB
DATA_LIMITS_MB = {
    "300MB": 300,
    "750MB": 750,
    "1.5GB": 1536,
    "2.5GB": 2560,
    "5GB": 5120,
    "4GB": 4096,
    "7.5GB": 7680,
    "12GB": 12288,
    "Unlimited": None
}

# Maps plan validity to minutes
VALIDITY_MINUTES = {
    "24 hours": 1440,
    "7 days": 10080,
    "30 days": 43200
}

def create_voucher(plan_data: str, validity: str, note: str = "ayosco_voucher"):
    """Creates a voucher on UniFi and returns the voucher code."""
    data_mb = DATA_LIMITS_MB.get(plan_data)
    minutes = VALIDITY_MINUTES.get(validity, 1440)

    payload = {
        "cmd": "create-voucher",
        "count": 1,
        "expire": minutes,
        "expire_number": 1,
        "expire_unit": minutes,
        "quota": 1,
        "note": note,
        "up": None,
        "down": None,
    }

    if data_mb:
        payload["bytes"] = data_mb

    create_response = requests.post(
        f"{UDM_IP}/proxy/network/api/s/{SITE_ID}/cmd/hotspot",
        headers=HEADERS,
        json=payload,
        verify=False
    )

    if create_response.status_code != 200:
        return None

    create_time = create_response.json()["data"][0]["create_time"]

    # Fetch the voucher using the create_time to find the exact one we just made
    fetch_response = requests.get(
        f"{UDM_IP}/proxy/network/api/s/{SITE_ID}/stat/voucher?create_time={create_time}",
        headers=HEADERS,
        verify=False
    )

    vouchers = fetch_response.json().get("data", [])
    if vouchers:
        return vouchers[0]["code"]

    return None
