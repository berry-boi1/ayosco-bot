import requests
import urllib3
import os
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

UDM_IP = os.getenv("UNIFI_IP")
API_KEY = os.getenv("UNIFI_API_KEY")

headers = {
    "X-API-KEY": API_KEY,
    "Accept": "application/json"
}

response = requests.get(
    f"{UDM_IP}/proxy/network/integration/v1/sites",
    headers=headers,
    verify=False
)

print("Status code:", response.status_code)
print("Response:", response.text)
