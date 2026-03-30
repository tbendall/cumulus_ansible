#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import argparse
import json

## Curl command

# curl -u 'cumulus:Lab1234!' --insecure -X GET "https://leaf1:8765/nvue_v1/?rev=<revid>&diff=applied"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser(description='Fetch NVUE config from devices')
parser.add_argument('--devices', nargs='+', required=True, help='List of device names')
parser.add_argument('--config_type', required=True, choices=['applied', 'candidate'], help='Config type to fetch')
parser.add_argument('--revision', help='Revision ID for candidate config (required when config_type is candidate)')
args = parser.parse_args()

if args.config_type == 'candidate' and not args.revision:
    parser.error('--revision is required when config_type is candidate')

devices = args.devices
config_type = args.config_type
revision = args.revision

auth = HTTPBasicAuth("cumulus","Lab1234!")
APPLIED_URL_TMPL = "https://{device}:8765/nvue_v1/?rev=applied&filled=false"
CANDIDATE_URL_TMPL = "https://{device}:8765/nvue_v1/?rev={revision}&filled=false"

MAX_WORKERS = 200
TIMEOUT = (5, 10)  # (connect, read)

def fetch(device: str, config_type: str, revision: str):
    if config_type == "applied":
        url = APPLIED_URL_TMPL.format(device=device)
    elif config_type == "candidate":
        url = CANDIDATE_URL_TMPL.format(device=device, revision=revision)
    try:
        r = requests.get(url, auth=auth, verify=False, timeout=TIMEOUT)
        r.raise_for_status()
        return device, {"ok": True, "data": r.json()}
    except Exception as e:
        return device, {"ok": False, "error": str(e), "url": url}


if __name__ == "__main__":
    results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch, d, config_type, revision) for d in devices]
        for f in as_completed(futures):
            device, result = f.result()
            results[device] = result

    for d, r in results.items():
        if r.get("ok") and isinstance(r.get("data"), dict):

            print(json.dumps(r['data']))