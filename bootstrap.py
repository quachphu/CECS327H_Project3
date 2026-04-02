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

import logging
from flask import Flask, request, jsonify

app = Flask(__name__) # Resources : https://www.youtube.com/watch?v=Z1RJmh_OqeA 

# Store registered peers: {node_id: url }
registered_peers = {}

logging.basicConfig(
    level=logging.INFO,
    format="[Bootstrap] %(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bootstrap")


@app.route("/", methods=["GET"]) # using resources : https://dev.to/jdxlabs/bootstrap-your-projects-with-docker-init-1po3
def index():
    return jsonify(
        {
            "message": "Bootstrap node is running!",
            "registered_peers": len(registered_peers),
        }
    )


@app.route("/register", methods=["POST"]) # using resources : https://www.youtube.com/watch?v=Z1RJmh_OqeA 
def register_peer():
    data = request.get_json()  # Register peer node with bootstrap.
    if not data or "node_id" not in data or "url" not in data:
        return jsonify({"error": "Missing node_id or url"}), 400

    node_id = data["node_id"]
    url = data["url"]
    registered_peers[node_id] = url
    logger.info(
        f"Registered peer: {node_id} at {url}  (total: {len(registered_peers)})"
    )

    return jsonify({"status": "registered", "node_id": node_id})


@app.route("/unregister", methods=["POST"]) # using resources : https://www.youtube.com/watch?v=Z1RJmh_OqeA
def unregister_peer():
    data = request.get_json()  # Remove peer from registry
    if not data or "node_id" not in data:
        return jsonify({"error": "Missing node_id"}), 400

    node_id = data["node_id"]
    if node_id in registered_peers:
        del registered_peers[node_id]
        logger.info(f"Unregistered peer: {node_id}  (total: {len(registered_peers)})")
    return jsonify({"status": "unregistered", "node_id": node_id})


# Return list of all registered peer URLs
@app.route("/peers", methods=["GET"])
def get_peers():
    peer_list = list(registered_peers.values())
    return jsonify({"peers": peer_list})


@app.route("/peers/detailed", methods=["GET"])
def get_peers_detailed():  # Return detailed peer info
    return jsonify({"peers": registered_peers})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
