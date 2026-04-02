"""
Resources :
1. https://www.geeksforgeeks.org/system-design/peer-to-peer-p2p-architecture/
2. https://docs.docker.com/reference/samples/flask
2. https://flask.palletsprojects.com/en/stable/quickstart/ 
3. https://p2pnetsuite.github.io/P2PNet/misc/bootstrapserver.html
4. https://www.youtube.com/watch?v=Rvfs6Xx3Kww
5. Professor Lecture and assignments from CECS 327H
6. https://docs.docker.com/compose/how-tos/networking/ 
7. https://docs.docker.com/guides/python/containerize/
"""

import os
import sys
import uuid
import time
import json
import logging
import threading
import requests
from flask import Flask, request, jsonify

# Configuration
NODE_ID = os.environ.get("NODE_ID", str(uuid.uuid4())[:8])
NODE_PORT = int(os.environ.get("NODE_PORT", 5000))
BOOTSTRAP_URL = os.environ.get("BOOTSTRAP_URL", "http://bootstrap:5000")

# The hostname other nodes use to reach us inside the Docker network
NODE_HOST = os.environ.get("NODE_HOST", f"node-{NODE_ID}")
NODE_URL = f"http://{NODE_HOST}:{NODE_PORT}"
DISCOVERY_INTERVAL = int(os.environ.get("DISCOVERY_INTERVAL", 10))
app = Flask(__name__)  #  I studied through this : https://flask.palletsprojects.com/en/stable/quickstart/ 

# Peer storage
peers = set()
message_log = []  # Message log for node

logging.basicConfig(
    level=logging.INFO,
    format=f"[Node {NODE_ID}] %(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(f"node-{NODE_ID}")


# Flask Routes
@app.route("/", methods=["GET"])
def index():
    return jsonify(
        {
            "message": f"Node {NODE_ID} is running!",
            "node_id": NODE_ID,
            "url": NODE_URL,
            "peers_count": len(peers),
        }
    )


@app.route("/register", methods=["POST"])
def register_peer():  # Register peer node with bootstrap
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing url"}), 400

    peer_url = data["url"]
    if peer_url != NODE_URL:
        peers.add(peer_url)
        logger.info(
            f"Peer registered directly: {peer_url}  (total peers: {len(peers)})"
        )

    return jsonify({"status": "registered", "node_id": NODE_ID})


@app.route("/peers", methods=["GET"])
def get_peers():  # return node peer list
    return jsonify({"peers": list(peers), "node_id": NODE_ID})


@app.route("/message", methods=["POST"])  # Receive a message from another peer
def receive_message():
    data = request.get_json()
    if not data or "sender" not in data or "msg" not in data:
        return jsonify({"error": "Missing sender or msg"}), 400
    sender = data["sender"]
    msg = data["msg"]
    timestamp = time.strftime("%H:%M:%S")

    entry = {"sender": sender, "msg": msg, "time": timestamp}
    message_log.append(entry)
    logger.info(f"Received message from {sender}: {msg}")

    return jsonify({"status": "received", "node_id": NODE_ID})


@app.route("/messages", methods=["GET"])
def get_messages():  # return all messages received by this node
    return jsonify({"node_id": NODE_ID, "messages": message_log})


@app.route("/send", methods=["POST"])
def send_message_api():  # Api to trigger
    data = request.get_json()
    if not data or "target" not in data or "msg" not in data:
        return jsonify({"error": "Missing target or msg"}), 400

    target_url = data["target"]
    msg = data["msg"]

    try:
        resp = requests.post(
            f"{target_url}/message",
            json={"sender": NODE_ID, "msg": msg},
            timeout=3,
        )
        return jsonify(
            {"status": "sent", "target": target_url, "response": resp.json()}
        )
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


@app.route("/broadcast", methods=["POST"])
def broadcast_message():
    # Broadcast message to ALL known peers
    data = request.get_json()
    if not data or "msg" not in data:
        return jsonify({"error": "Missing msg"}), 400

    msg = data["msg"]
    results = {}
    for peer_url in list(peers):
        try:
            resp = requests.post(
                f"{peer_url}/message",
                json={"sender": NODE_ID, "msg": msg},
                timeout=3,
            )
            results[peer_url] = "delivered"
        except Exception as e:
            results[peer_url] = f"failed: {e}"

    logger.info(f"Broadcast message to {len(results)} peers")
    return jsonify({"status": "broadcast_complete", "results": results})


# Register this node with bootstrap node
def register_with_bootstrap():
    max_retries = 10
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{BOOTSTRAP_URL}/register",
                json={"node_id": NODE_ID, "url": NODE_URL},
                timeout=5,
            )
            if resp.status_code == 200:
                logger.info(f"Registered with bootstrap at {BOOTSTRAP_URL}")
                return True
        except Exception as e:
            logger.warning(
                f"Bootstrap registration attempt {attempt + 1}/{max_retries} failed: {e}"
            )
        time.sleep(2)

    logger.error("Could not register with bootstrap after retries")
    return False


# Fetch peer list from bootstrap node
def discover_peers_from_bootstrap():
    try:
        resp = requests.get(f"{BOOTSTRAP_URL}/peers", timeout=5)
        if resp.status_code == 200:
            peer_list = resp.json().get("peers", [])
            new_count = 0
            for url in peer_list:
                if url != NODE_URL and url not in peers:
                    peers.add(url)
                    new_count += 1
            if new_count > 0:
                logger.info(
                    f"Discovered {new_count} new peers from bootstrap (total: {len(peers)})"
                )
    except Exception as e:
        logger.warning(f"Failed to discover peers from bootstrap: {e}")


def discover_peers_from_peers():  # Ask existing peers for their peer lists
    new_count = 0
    for peer_url in list(peers):
        try:
            resp = requests.get(f"{peer_url}/peers", timeout=3)
            if resp.status_code == 200:
                their_peers = resp.json().get("peers", [])
                for url in their_peers:
                    if url != NODE_URL and url not in peers:
                        peers.add(url)
                        new_count += 1
        except Exception:
            pass  # Peer might be unavailable

    if new_count > 0:
        logger.info(
            f"Discovered {new_count} new peers via gossip (total: {len(peers)})"
        )


def periodic_discovery():
    register_with_bootstrap()
    time.sleep(2)
    discover_peers_from_bootstrap()  # one-time initial peer list from bootstrap
    logger.info("Initial bootstrap discovery complete — switching to gossip-only mode")

    # After the initial discovery ,the bootstrap node is no longer needed then we test by talking directly to each other.
    while True:
        time.sleep(DISCOVERY_INTERVAL)
        discover_peers_from_peers()


# Main
if __name__ == "__main__":
    logger.info(f"Starting node {NODE_ID} at {NODE_URL}")
    discovery_thread = threading.Thread(target=periodic_discovery, daemon=True)
    discovery_thread.start()

    app.run(host="0.0.0.0", port=NODE_PORT)
