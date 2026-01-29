#!/usr/bin/python3


import requests
from requests.auth import HTTPBasicAuth
import json
import time

#curl -u cumulus:Lab123 --insecure -l -X  GET https://leaf1:8765/nvue_v1/?rev=applied&filled=false

devices = ["leaf1","leaf2","leaf3","leaf4"]



auth = HTTPBasicAuth(username="cumulus",password="Lab123")
mime_header = {"Content-Type": "application/json"}

mac_dict = {}

if __name__ == "__main__":

    for device in devices:

        r = requests.get(url="https://{device}:8765/nvue_v1/evpn/vni/100/mac".format(device=device),
                        auth=auth,verify=False)
        #print("=======Current Applied Revision=======")
        #print(json.dumps(r.json(), indent=2))

        mac_dict[device] = r.json()

    {print(f"{k} has MACs {v.keys()}") for k,v in mac_dict.items()}