#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys



urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#devices = ["leaf1","leaf2","leaf3","leaf4"]

devices = sys.argv[1:]

auth = HTTPBasicAuth("cumulus","Lab1234!")
URL_TMPL = "https://{device}:8765/nvue_v1/vrf/default/router/bgp/address-family/l2vpn-evpn/loc-rib"

MAX_WORKERS = 200
TIMEOUT = (5, 10)  # (connect, read)

def fetch(device: str):
    url = URL_TMPL.format(device=device)
    try:
        r = requests.get(url, auth=auth, verify=False, timeout=TIMEOUT)
        r.raise_for_status()
        return device, {"ok": True, "status": r.status_code, "data": r.json()}
    except Exception as e:
        return device, {"ok": False, "error": str(e), "url": url}

if __name__ == "__main__":
    results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(fetch, d) for d in devices]
        for f in as_completed(futures):
            device, result = f.result()
            results[device] = result

    for d, r in results.items():
        if r.get("ok") and isinstance(r.get("data"), dict):
            for entry in r['data']['rd']:
                
                rib_dict = {k:v for k,v in r['data']['rd'][entry]['route-type'].items() if k == '2'}

                print(rib_dict)

            #print(f"{d} has VNIs {list(r['data'].keys())}")
        else:
            print(f"{d} failed: {r.get('error')}")