# Group Project 3: A Bite of Peer-to-Peer

**CECS 327 – Intro to Networks and Distributed Computing**

## Overview

A containerized Peer-to-Peer (P2P) network consisting of 50 nodes, each running as a Docker container. Nodes register with a bootstrap node for initial discovery, then communicate directly with each other using a gossip-based peer discovery protocol.

## Architecture

```
┌──────────────────────────────────────────────┐
│               Bootstrap Node                  │
│  (Central registry for initial discovery)     │
│  - /register   → peers register here          │
│  - /peers      → returns all registered URLs  │
└────────────┬─────────────────┬───────────────┘
             │  (initial)      │
     ┌───────▼──┐       ┌─────▼────┐
     │  Node 1  │◄─────►│  Node 2  │    ← direct P2P
     └───┬──────┘       └────┬─────┘      communication
         │                   │
     ┌───▼──────┐       ┌────▼─────┐
     │  Node 3  │◄─────►│  Node N  │
     └──────────┘       └──────────┘
         ... (up to 50 nodes) ...
```

### How It Works

1. **Startup**: Each node generates a unique ID and starts a Flask HTTP server.
2. **Registration**: On startup, each node registers its ID and URL with the bootstrap node.
3. **Peer Discovery**: Nodes periodically fetch the peer list from:
   - The bootstrap node (initial discovery)
   - Other known peers (gossip protocol — decentralized discovery)
4. **Messaging**: Nodes communicate directly via HTTP POST to `/message`.
5. **Independence**: After initial discovery, the bootstrap is not needed for communication.

## Prerequisites

- **Docker** (v20+)
- **Docker Compose** (v2+)
- **Python 3.9+** (for running the test script on the host)

## Quick Start

### 1. Build and Run

```bash
# Clone/copy all files into a directory
cd p2p-system

# Build and start all 50 nodes + bootstrap
docker-compose up -d --build

# Wait ~20 seconds for all nodes to register
sleep 20

# Verify containers are running
docker ps | head -20
```

### 2. Verify Bootstrap

```bash
# Check bootstrap is running
curl http://localhost:5000/

# See all registered peers
curl http://localhost:5000/peers
```

### 3. Verify Individual Nodes

```bash
# Check node-1
curl http://localhost:5001/

# Check node-1's peer list
curl http://localhost:5001/peers
```

### 4. Send Messages Between Nodes

```bash
# Send message from Node2 to Node1
curl -X POST http://localhost:5001/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "node-2", "msg": "Hello Node1!"}'

# Send message from Node1 to Node2
curl -X POST http://localhost:5002/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "node-1", "msg": "Hey Node2, how are you?"}'

# Broadcast from Node-1 to all peers
curl -X POST http://localhost:5001/broadcast \
  -H "Content-Type: application/json" \
  -d '{"msg": "Hello everyone from Node-1!"}'
```

### 5. Run the Full Test Suite

```bash
# Install test dependencies (host machine)
pip install requests

# Run comprehensive tests across all 50 nodes
python test_network.py 50
```

The test script runs 8 tests:
1. Bootstrap health check
2. Individual node verification
3. Direct messaging between node pairs
4. Broadcast from one node to all peers
5. Chain messaging across 20 nodes
6. Random messaging (30 random node pairs)
7. Message log verification
8. Gossip-based peer discovery verification

### 6. Check Logs

```bash
# View bootstrap logs
docker logs bootstrap

# View a specific node's logs
docker logs node-1

# Follow logs in real-time
docker logs -f node-5
```

### 7. Shut Down

```bash
docker-compose down
```

## Changing the Number of Nodes

To generate a compose file with a different number of nodes:

```bash
pip install pyyaml
python generate_compose.py 100   # generates docker-compose.yml with 100 nodes
docker-compose up -d --build
```

## API Endpoints

### Bootstrap Node (port 5000)

| Endpoint           | Method | Description                     |
|-------------------|--------|---------------------------------|
| `/`               | GET    | Health check                    |
| `/register`       | POST   | Register a peer `{node_id, url}`|
| `/peers`          | GET    | List all registered peer URLs   |
| `/peers/detailed` | GET    | List peers with IDs             |

### Peer Nodes (ports 5001–5050)

| Endpoint     | Method | Description                             |
|-------------|--------|-----------------------------------------|
| `/`         | GET    | Health check + node info                |
| `/register` | POST   | Direct peer registration `{url}`        |
| `/peers`    | GET    | This node's known peer list             |
| `/message`  | POST   | Receive a message `{sender, msg}`       |
| `/messages` | GET    | View all received messages              |
| `/send`     | POST   | Send msg to a target `{target, msg}`    |
| `/broadcast`| POST   | Broadcast msg to all peers `{msg}`      |

## File Structure

```
p2p-system/
├── bootstrap.py            # Bootstrap node (central registry)
├── bootstrap.Dockerfile    # Dockerfile for bootstrap
├── node.py                 # P2P node (peer application)
├── Dockerfile              # Dockerfile for peer nodes
├── docker-compose.yml      # Compose file (50 nodes + bootstrap)
├── generate_compose.py     # Script to regenerate compose with N nodes
├── test_network.py         # Comprehensive test suite
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Design Decisions

- **Flask** was chosen for simplicity — each node runs a lightweight HTTP server.
- **Gossip protocol**: Nodes don't just rely on the bootstrap; they also ask peers for their peer lists, enabling decentralized discovery.
- **Threading**: Background discovery runs in a daemon thread, separate from the Flask server.
- **Docker networking**: All containers share a `p2p-net` bridge network, allowing hostname-based communication (e.g., `http://node-1:5000`).

