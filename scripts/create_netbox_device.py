#!/usr/bin/python3

import pynetbox
import yaml

yaml_file = "leaf1.yaml"

# ---------------------------------------------------------
# Core NetBox Client Wrapper
# ---------------------------------------------------------
class NetBoxClient:
    def __init__(self, url, token):
        self.nb = pynetbox.api(url, token=token)

    def get_device(self, name):
        return self.nb.dcim.devices.get(name=name)

    def create_device(self, data):
        return self.nb.dcim.devices.create(data)

    def get_interface(self, device_id, name):
        return self.nb.dcim.interfaces.get(device_id=device_id, name=name)

    def create_interface(self, data):
        return self.nb.dcim.interfaces.create(data)

    def get_ip(self, address):
        return self.nb.ipam.ip_addresses.get(address=address)

    def create_ip(self, data):
        return self.nb.ipam.ip_addresses.create(data)


# ---------------------------------------------------------
# Device Definition (from YAML)
# ---------------------------------------------------------
class DeviceDefinition:
    def __init__(self, data):
        self.hostname = data["hostname"]
        self.mgmt_ip = data["mgmt_ip"]
        self.lo_ip = data["lo_ip"]
        self.bgp_asn = data["bgp_asn"]
        self.bgp_routerid = data["bgp_routerid"]
        self.interfaces = data["interfaces"]
        self.neighbors = data["neighbors"]


# ---------------------------------------------------------
# NetBox Device Object
# ---------------------------------------------------------
class NetBoxDevice:
    def __init__(self, client, definition):
        self.client = client
        self.definition = definition
        self.device = None

    def ensure(self):
        self.device = self.client.get_device(self.definition.hostname)
        if not self.device:
            self.device = self.client.create_device({
                "name": self.definition.hostname,
                "device_type": 1,
                "device_role": 1,
                "site": 1
            })
        return self.device

    def set_primary_ip(self, ip_obj):
        if self.device.primary_ip4 is None or self.device.primary_ip4.id != ip_obj.id:
            self.device.update({"primary_ip4": ip_obj.id})

# ---------------------------------------------------------
# NetBox ASN Object
# ---------------------------------------------------------

class ASNAllocator:
    def __init__(self, client):
        self.client = client

    def get_range(self, name):
        ranges = self.client.nb.ipam.asn_ranges.filter(name=name)
        return ranges[0] if ranges else None

    def get_used_asns(self, start, end):
        used = set()
        asns = self.client.nb.ipam.asns.filter(asn__gte=start, asn__lte=end)
        for a in asns:
            used.add(a.asn)
        return used

    def allocate(self, range_name):
        asn_range = self.get_range(range_name)
        if not asn_range:
            raise ValueError(f"ASN range '{range_name}' not found in NetBox")

        start = asn_range.start
        end = asn_range.end

        used = self.get_used_asns(start, end)

        for candidate in range(start, end + 1):
            if candidate not in used:
                # Create ASN object in NetBox
                asn_obj = self.client.nb.ipam.asns.create({
                    "asn": candidate,
                    "description": f"Allocated dynamically from {range_name}"
                })
                return candidate

        raise RuntimeError(f"No free ASNs available in range {range_name}")

# ---------------------------------------------------------
# NetBox Interface Object
# ---------------------------------------------------------
class NetBoxInterface:
    def __init__(self, client, device):
        self.client = client
        self.device = device

    def ensure(self, iface):
        nb_iface = self.client.get_interface(self.device.id, iface["id"])
        if not nb_iface:
            nb_iface = self.client.create_interface({
                "device": self.device.id,
                "name": iface["id"],
                "type": iface["type"],
                "description": iface.get("desc", "")
            })
        else:
            nb_iface.update({
                "type": iface["type"],
                "description": iface.get("desc", "")
            })
        return nb_iface


# ---------------------------------------------------------
# NetBox IP Address Object
# ---------------------------------------------------------
class NetBoxIPAddress:
    def __init__(self, client):
        self.client = client

    def ensure(self, address, iface=None):
        ip_obj = self.client.get_ip(address)
        if not ip_obj:
            data = {"address": address, "status": "active"}
            if iface:
                data["assigned_object_type"] = "dcim.interface"
                data["assigned_object_id"] = iface.id
            ip_obj = self.client.create_ip(data)
        else:
            if iface and not ip_obj.assigned_object_id:
                ip_obj.update({
                    "assigned_object_type": "dcim.interface",
                    "assigned_object_id": iface.id
                })
        return ip_obj


# ---------------------------------------------------------
# Device Manager (Orchestrator)
# ---------------------------------------------------------
class DeviceManager:
    def __init__(self, client, definition):
        self.client = client
        self.definition = definition
        self.asn_allocator = ASNAllocator(client)


    def apply(self):
        device_obj = NetBoxDevice(self.client, self.definition)
        device = device_obj.ensure()

        # Determine ASN range
        if "leaf" in self.definition.hostname.lower():
            range_name = "ASN_LEAFS"

        # Allocate ASN if missing
        if not device.custom_fields.get("bgp_asn"):
            asn = self.asn_allocator.allocate(range_name)
            device.update({"custom_fields": {"bgp_asn": asn}})
        else:
            asn = device.custom_fields["bgp_asn"]


        iface_mgr = NetBoxInterface(self.client, device)
        ip_mgr = NetBoxIPAddress(self.client)

        # Management IP
        mgmt_ip = ip_mgr.ensure(self.definition.mgmt_ip)
        device_obj.set_primary_ip(mgmt_ip)

        # Interfaces + IPs
        for iface in self.definition.interfaces:
            nb_iface = iface_mgr.ensure(iface)
            ip_mgr.ensure(iface["ip"], nb_iface)

        # Neighbors (simple tag example)
        tags = [n["name"] for n in self.definition.neighbors]
        device.update({"tags": tags})

        return device


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    with open(f"{yaml_file}") as f:
        data = yaml.safe_load(f)

    definition = DeviceDefinition(data)

    print(definition.bgp_asn)
#    client = NetBoxClient("https://netbox.example.com", "YOUR_TOKEN")
#
#    manager = DeviceManager(client, definition)
#    manager.apply()
#
#    print(f"Device {definition.hostname} synced to NetBox.")
