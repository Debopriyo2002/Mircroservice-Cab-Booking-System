
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory driver data for local testing only.
drivers = {
    1: {"id": 1, "status": "AVAILABLE"}
}


@app.get("/health")
def health():
    return jsonify({"service": "driver-service", "status": "UP"})


@app.get("/api/v1/drivers/available")
def available_drivers():
    available = [
        driver for driver in drivers.values()
        if driver["status"] == "AVAILABLE"
    ]
    return jsonify({"drivers": available})


@app.put("/api/v1/drivers/<int:driver_id>/status")
def update_driver_status(driver_id):
    driver = drivers.get(driver_id)

    if driver is None:
        return jsonify({"error": "Driver not found"}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status", "").upper()

    if status not in {"AVAILABLE", "BUSY"}:
        return jsonify({"error": "Invalid driver status"}), 400

    driver["status"] = status
    return jsonify({"driver": driver}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=False)
