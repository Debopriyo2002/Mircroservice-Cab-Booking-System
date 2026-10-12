
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({
        "service": "payment-service",
        "status": "UP"
    })


@app.post("/api/v1/payments")
def process_payment():
    data = request.get_json(silent=True) or {}

    trip_id = data.get("trip_id")
    amount = data.get("amount")
    method = str(data.get("method", "UPI")).upper()

    if trip_id is None or amount is None:
        return jsonify({
            "error": "trip_id and amount are required",
            "status": "FAILED"
        }), 400

    if method == "FAIL":
        return jsonify({
            "trip_id": trip_id,
            "status": "FAILED",
            "message": "Simulated payment failure"
        }), 400

    return jsonify({
        "trip_id": trip_id,
        "status": "SUCCESS",
        "message": "Simulated payment successful"
    }), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5004, debug=False)
