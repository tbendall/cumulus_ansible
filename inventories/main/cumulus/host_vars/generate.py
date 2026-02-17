
import json
from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict, TypedDict
from netaddr import *

spine_count = 4
leaf_count = 4
wan_count = 2

leaf_loopback_supernet = list(IPNetwork("10.10.10.0/24"))
leaf_asn_start = 65000

spine_loopback_supernet = list(IPNetwork("10.10.20.0/24"))
spine_asn_start = 65100

nodes = {}

class InterfaceDict(TypedDict):
    id: str
    ip: str
    type: str
    desc: str

@dataclass
class Link:
    a_int: str
    a_node: str
    b_int: str
    b_node: str


@dataclass
class Node:
    hostname: str
    lo_ip: str 
    bgp_asn: str
    bgp_router_id: str
    total_interfaces: List[str]
    interfaces: List[InterfaceDict] = field(default_factory=list)
#    neighbours: List[str]
    used_ifaces: List[str] = field(default_factory=list)

    def allocate_iface(self, *args) -> Optional[str]:
        if len(args)>0:
            iface = args[0] 
            if iface not in self.used_ifaces and iface in self.total_interfaces:
                self.used_ifaces.append(iface)
                return iface
            else: 
                new_int = next((x for x in self.total_interfaces if x not in self.used_ifaces), None)
                return new_int
        else:
            new_int = next((x for x in self.total_interfaces if x not in self.used_ifaces), None)
            self.used_ifaces.append(new_int)
            return new_int

    def to_dict(self) -> Dict:
        return {
            "hostname": self.hostname,
            "lo_ip": self.lo_ip,
            "bgp_router_id": self.bgp_router_id,
            "interfaces": self.interfaces,
#            "neighbours": self.neighbours,
            "used_ifaces": self.used_ifaces

        }

spines = [f"spine-{x}" for x in range(1,spine_count+1)]
leafs = [f"leaf-{x}" for x in range(1,leaf_count+1)]

def create_links():

    node_links = {(spine, leaf) for spine in spines for leaf in leafs}

    for spine, leaf in node_links:

        leaf_iface = nodes[leaf].allocate_iface()

        nodes[spine].allocate_iface(leaf_iface)

        

#    if leaf_iface:
#        spine_iface = node.allocate_iface(leaf_iface)

def create_nodes():

    # Leafs
    for leaf in leafs:

        # Allocate Loopback 
        loopback = str(IPNetwork(leaf_loopback_supernet[0]))

        # Allocate Router_ID
        router_id = str(leaf_loopback_supernet[0])

        loopback_entry = {

            "id": "lo",
            "ip": loopback,
            "type": "loopback",
            "desc": "Router Loopback"

        }

        leaf_obj = Node(
            hostname = leaf,
            total_interfaces=["swp1","swp2","swp3","swp4"],
            lo_ip = loopback,
            bgp_asn = leaf_asn_start + leafs.index(leaf),
            bgp_router_id = router_id,
            interfaces = loopback_entry
            
        ) 

        nodes[leaf] = leaf_obj

#        create_links(leaf)

        leaf_loopback_supernet.pop(0)

    for spine in spines:

        count = spines.index(spine)

        # Allocate Loopback 
        loopback = str(IPNetwork(spine_loopback_supernet[count]))

        # Allocate Router_ID
        router_id = str(spine_loopback_supernet[count])

        loopback_entry = {

            "id": "lo",
            "ip": loopback,
            "type": "loopback",
            "desc": "Router Loopback"

        }

        spine_obj = Node(
            hostname = spine,
            total_interfaces=["swp1","swp2","swp3","swp4"],
            lo_ip = loopback,
            bgp_asn = spine_asn_start + count,
            bgp_router_id = router_id,
            interfaces = loopback_entry
            
        ) 

        nodes[spine] = spine_obj

        spine_loopback_supernet.pop(0)    

    return nodes




if __name__ == "__main__":

    nodes = create_nodes()

    links = create_links()

    print(nodes["spine-1"])
