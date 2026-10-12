
from flask import Flask, request, jsonify

from database import (
    initialize_database,
    create_trip,
    get_trip,
    update_trip
)
from saga import execute, release_driver, driver_breaker, payment_breaker

app = Flask(__name__)

# Create the trip database and table on startup.
initialize_database()


@app.get("/health")
def health():
    return jsonify({
        "service": "trip-service",
        "status": "UP"
    }), 200


@app.post("/api/v1/trips")
def create_trip_api():
    data = request.get_json(silent=True) or {}

    rider_id = data.get("rider_id")
    fare = data.get("fare")
    payment_method = data.get("payment_method", "UPI")
    pickup = data.get("pickup_location", "")
    drop = data.get("drop_location", "")

    if rider_id is None or fare is None:
        return jsonify({
            "error": "rider_id and fare are required"
        }), 400

    try:
        fare = float(fare)
        if fare <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"error": "fare must be a positive number"}), 400

    if not isinstance(payment_method, str) or not payment_method.strip():
        return jsonify({"error": "payment_method must be a non-empty string"}), 400

    trip_id = create_trip(
        rider_id=rider_id,
        pickup=pickup,
        drop=drop,
        fare=fare,
        payment_method=payment_method.strip().upper()
    )

    try:
        result = execute(
            trip_id=trip_id,
            fare=fare,
            payment_method=payment_method.strip().upper()
        )

        trip = get_trip(trip_id)
        return jsonify({
            "message": "Trip booked successfully",
            "trip": trip,
            "result": result
        }), 201

    except Exception as exc:
        trip = get_trip(trip_id)
        return jsonify({
            "message": "Trip booking failed",
            "error": str(exc),
            "trip": trip
        }), 502


@app.get("/api/v1/trips/<int:trip_id>")
def get_trip_v1(trip_id):
    trip = get_trip(trip_id)

    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    return jsonify({
        "trip_id": trip["id"],
        "rider_id": trip["rider_id"],
        "driver_id": trip["driver_id"],
        "status": trip["status"],
        "fare": trip["fare"]
    }), 200


@app.get("/api/v2/trips/<int:trip_id>")
def get_trip_v2(trip_id):
    trip = get_trip(trip_id)

    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    return jsonify({
        "trip_id": trip["id"],
        "rider_id": trip["rider_id"],
        "driver_id": trip["driver_id"],
        "status": trip["status"],
        "fare": trip["fare"],
        "pickup_location": trip["pickup_location"],
        "drop_location": trip["drop_location"],
        "estimated_time": "Not available"
    }), 200


@app.put("/api/v1/trips/<int:trip_id>/cancel")
def cancel_trip(trip_id):
    trip = get_trip(trip_id)

    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    if trip["status"] == "CANCELLED":
        return jsonify({
            "message": "Trip is already cancelled",
            "trip": trip
        }), 200

    driver_id = trip["driver_id"]

    if driver_id is not None:
        try:
            release_driver(driver_id)
        except Exception as exc:
            return jsonify({
                "error": "Could not release the driver",
                "details": str(exc)
            }), 502

    update_trip(trip_id, status="CANCELLED")

    return jsonify({
        "message": "Trip cancelled successfully",
        "trip": get_trip(trip_id)
    }), 200


@app.get("/api/v1/resilience")
def resilience_status():
    return jsonify({
        "driver_circuit_breaker": driver_breaker.get_state(),
        "payment_circuit_breaker": payment_breaker.get_state()
    }), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003, debug=False)
