from flask import Flask, jsonify, request
from datetime import datetime, timezone

app = Flask(__name__)

# In-memory registry: { "driver-service": {"url": "http://localhost:5002", "registered_at": "..."} }
registry = {}


def now():
    return datetime.now(timezone.utc).isoformat()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "service-registry"}), 200


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    url = data.get("url")

    if not name or not url:
        return jsonify({"error": "Both 'name' and 'url' are required"}), 400

    # Re-registering the same name overwrites it, so restarts just work
    registry[name] = {"url": url.rstrip("/"), "registered_at": now()}
    return jsonify({"message": f"{name} registered", "name": name, "url": registry[name]["url"]}), 201


@app.route("/services/<name>", methods=["GET"])
def lookup(name):
    entry = registry.get(name)
    if not entry:
        return jsonify({"error": f"Service '{name}' not found"}), 404
    return jsonify({"name": name, "url": entry["url"]}), 200


@app.route("/services", methods=["GET"])
def list_services():
    return jsonify({n: e["url"] for n, e in registry.items()}), 200


@app.route("/deregister/<name>", methods=["DELETE"])
def deregister(name):
    if registry.pop(name, None) is None:
        return jsonify({"error": f"Service '{name}' not found"}), 404
    return jsonify({"message": f"{name} deregistered"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010)