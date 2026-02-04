
import json
from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict
from netaddr import *

spine_count = 4
leaf_count = 4
wan_count = 2

leaf_loopback_supernet = list(IPNetwork("10.10.10.0/24"))
leaf_asn_start = 65000

spine_loopback_supernet = list(IPNetwork("10.10.20.0/24"))
spine_asn_start = 65100

nodes = {}

@dataclass
class Node:
    hostname: str
    lo_ip: str 
    bgp_asn: str
    bgp_router_id: str
    interfaces: List[str]


    def to_dict(self) -> Dict:
        return {
            "hostname": self.hostname,
            "lo_ip": self.lo_ip,
            "bgp_router_id": self.bgp_router_id,
            "interfaces": self.interfaces

        }

def create_nodes():

    for i in range(1,1+leaf_count):

        # Allocate Loopback 
        loopback = str(IPNetwork(leaf_loopback_supernet[0]))

        # Allocate Router_ID
        router_id = str(leaf_loopback_supernet[0])

        leaf = Node(f"leaf-{i}",loopback,leaf_asn_start+i,router_id,["swp1","swp2"])

        nodes.append(leaf.to_dict())

        leaf_loopback_supernet.pop(0)

    return nodes




if __name__ == "__main__":
    
    # Create set of Loopbacks

    print(create_nodes())
