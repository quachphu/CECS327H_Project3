"""
Resources : 
1. https://codezup.com/flask-app-deployment-on-docker-compose/
2. https://betterstack.com/community/guides/scaling-docker/docker-compose-getting-started/ 
"""

import sys
import yaml

NUM_NODES = int(sys.argv[1]) if len(sys.argv) > 1 else 50

compose = {
    "version": "3.8",
    "services": {},
    "networks": {
        "p2p-net": {
            "driver": "bridge",
        }
    },
}

# Bootstrap node
compose["services"]["bootstrap"] = {
    "build": {
        "context": ".",
        "dockerfile": "bootstrap.Dockerfile",
    },
    "container_name": "bootstrap",
    "ports": ["8000:5000"],
    "networks": ["p2p-net"],
}

# Peer nodes
for i in range(1, NUM_NODES + 1):
    node_name = f"node-{i}"
    host_port = 8000 + i  # maps to host ports 8001, 8002, ...

    compose["services"][node_name] = {
        "build": {
            "context": ".",
            "dockerfile": "Dockerfile",
        },
        "container_name": node_name,
        "environment": [
            f"NODE_ID=node-{i}",
            f"NODE_HOST={node_name}",
            "NODE_PORT=5000",
            "BOOTSTRAP_URL=http://bootstrap:5000",
            "DISCOVERY_INTERVAL=10",
        ],
        "ports": [f"{host_port}:5000"],
        "depends_on": ["bootstrap"],
        "networks": ["p2p-net"],
    }

with open("docker-compose.yml", "w") as f:
    yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

print(f"Generated docker-compose.yml with 1 bootstrap + {NUM_NODES} peer nodes")
print(f"  Bootstrap: localhost:8000")
print(f"  Nodes: localhost:8001 - localhost:{8000 + NUM_NODES}")
