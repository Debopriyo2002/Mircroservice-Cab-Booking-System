
import os
import requests

from database import create_trip, get_trip, update_trip
from circuit_breaker import CircuitBreaker


DRIVER_SERVICE_URL = os.getenv(
    "DRIVER_SERVICE_URL", "http://localhost:5002"
)
PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL", "http://localhost:5004"
)

driver_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=10
)

payment_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=10
)

REQUEST_TIMEOUT = 3


def reserve_driver():
    """Ask Driver Service for an available driver."""
    response = requests.get(
        f"{DRIVER_SERVICE_URL}/api/v1/drivers/available",
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    data = response.json()

    # Adapt this extraction to the actual Driver Service response.
    drivers = data.get("drivers", data if isinstance(data, list) else [])

    if not drivers:
        raise RuntimeError("No available drivers")

    driver = drivers[0]
    driver_id = driver.get("id", driver.get("driver_id"))

    if driver_id is None:
        raise RuntimeError("Driver response does not contain an ID")

    # Reserve the driver using the team's status API.
    response = requests.put(
        f"{DRIVER_SERVICE_URL}/api/v1/drivers/{driver_id}/status",
        json={"status": "BUSY"},
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()

    return driver_id


def release_driver(driver_id):
    """Compensating action: make the driver available again."""
    response = requests.put(
        f"{DRIVER_SERVICE_URL}/api/v1/drivers/{driver_id}/status",
        json={"status": "AVAILABLE"},
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()


def process_payment(trip_id, fare, payment_method):
    """Request simulated payment from Payment Service."""
    response = requests.post(
        f"{PAYMENT_SERVICE_URL}/api/v1/payments",
        json={
            "trip_id": trip_id,
            "amount": fare,
            "method": payment_method
        },
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    result = response.json()

    if result.get("status", "").upper() in {
        "FAILED", "DECLINED", "ERROR"
    }:
        raise RuntimeError("Payment failed")

    return result


def execute(trip_id, fare, payment_method="UPI",
            rider_id=None, pickup=None, drop=None):
    """
    Execute the booking Saga.

    Order:
    1. Reserve driver
    2. Process payment
    3. Confirm trip

    If payment fails, release the driver and cancel the trip.
    """
    trip = get_trip(trip_id)

    if not trip:
        raise RuntimeError("Trip not found")

    driver_id = None

    try:
        driver_id = driver_breaker.call(reserve_driver)
        update_trip(
            trip_id,
            driver_id=driver_id,
            status="DRIVER_RESERVED",
            payment_method=payment_method
        )

        # The FAIL method is intended for the project's
        # simulated payment-failure demonstration.
        if payment_method.upper() == "FAIL":
            raise RuntimeError("Simulated payment failure")

        payment_breaker.call(
            process_payment, trip_id, fare, payment_method
        )

        update_trip(trip_id, status="CONFIRMED")

        return {
            "trip_id": trip_id,
            "driver_id": driver_id,
            "status": "CONFIRMED"
        }

    except Exception as exc:
        if driver_id is not None:
            try:
                release_driver(driver_id)
            except Exception as compensation_error:
                update_trip(trip_id, status="COMPENSATION_FAILED")
                raise RuntimeError(
                    f"{exc}; driver release also failed: "
                    f"{compensation_error}"
                ) from exc

        update_trip(trip_id, status="CANCELLED")

        raise RuntimeError(
            f"Booking failed: {exc}. Trip cancelled."
        ) from exc
