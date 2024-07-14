import requests
import json
import time
import random
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink

# OpenDaylight base URL
ODL_URL = 'http://localhost:8181/restconf/config/'

# Authentication
AUTH = ('admin', 'admin')

# Headers
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

# Load balancer configuration
SERVICE_IP = "10.0.0.100/32"
SOURCE_IP = "10.0.0.1/32"
TARGET_IPS = ["10.0.0.2/32", "10.0.0.3/32"]
IDLE_TIMEOUT = 10

def add_flow(switch_id, flow_id, flow):
    url = f"{ODL_URL}/opendaylight-inventory:nodes/node/{switch_id}/table/0/flow/{flow_id}"
    response = requests.put(url, data=json.dumps(flow), headers=HEADERS, auth=AUTH)
    if response.status_code in [200, 201]:
        print(f"Flow {flow_id} successfully added to {switch_id}")
    else:
        print(f"Error adding flow {flow_id} to {switch_id}: {response.status_code} {response.text}")

def delete_flows(switch_id):
    url = f"{ODL_URL}/opendaylight-inventory:nodes/node/{switch_id}/table/0"
    response = requests.delete(url, headers=HEADERS, auth=AUTH)
    if response.status_code == 200:
        print(f"All flows deleted from {switch_id}")
    elif response.status_code == 404:
        print(f"No flows to delete from {switch_id}")
    else:
        print(f"Error deleting flows from {switch_id}: {response.status_code} {response.text}")

def create_flow(match, actions, priority=100):
    return {
        "flow": [{
            "id": str(random.randint(1, 65535)),
            "match": match,
            "instructions": {
                "instruction": [{
                    "order": 0,
                    "apply-actions": {
                        "action": actions
                    }
                }]
            },
            "priority": priority,
            "idle-timeout": IDLE_TIMEOUT,
            "hard-timeout": 0,
            "table_id": 0
        }]
    }

def setup_mininet():
    net = Mininet(controller=RemoteController, link=TCLink)

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')

    s1 = net.addSwitch('s1')

    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s1)

    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    net.start()

    h1.setIP('10.0.0.1/24')
    h2.setIP('10.0.0.2/24')
    h3.setIP('10.0.0.3/24')

    return net

def generate_traffic(net):
    h1 = net.get('h1')
    h1.cmd('ping 10.0.0.100')

def main():
    net = setup_mininet()
    switch_id = "openflow:1"
    current_index = 0 

    delete_flows(switch_id)

    arp_match = {
        "ethernet-match": {
            "ethernet-type": {
                "type": "0x0806"
            },
            "ethernet-destination": {
                "address": "ff:ff:ff:ff:ff:ff"
            }
        },
        "arp-target-transport-address": SERVICE_IP
    }

    arp_actions = [
        {"order": 0, "output-action": {"output-node-connector": "NORMAL"}}
    ]

    arp_flow = create_flow(arp_match, arp_actions, priority=1000)
    add_flow(switch_id, arp_flow['flow'][0]['id'], arp_flow)

    while True:

        target_ip = TARGET_IPS[current_index]
        print(f"Redirecting traffic from {SOURCE_IP} to {target_ip}")

        current_index = (current_index + 1) % len(TARGET_IPS)

        ip_match = {
            "ipv4-source": SOURCE_IP,
            "ipv4-destination": SERVICE_IP,
            "ethernet-match": {
                "ethernet-type": {
                    "type": "0x0800"
                }
            }
        }

        ip_actions = [
            {"order": 0, "set-dl-dst-action": {"address": "00:00:00:00:00:01"}},
            {"order": 1, "set-nw-dst-action": {"ipv4-address": target_ip}},
            {"order": 2, "output-action": {"output-node-connector": "NORMAL"}}
        ]

        ip_flow = create_flow(ip_match, ip_actions)
        add_flow(switch_id, ip_flow['flow'][0]['id'], ip_flow)

        generate_traffic(net)
        time.sleep(IDLE_TIMEOUT)

if __name__ == "__main__":
    main()
