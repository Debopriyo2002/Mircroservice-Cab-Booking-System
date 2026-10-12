
import time
from circuit_breaker import CircuitBreaker


breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=10
)


def failing_service():
    raise RuntimeError("Simulated service failure")


def working_service():
    return "Service recovered successfully"


print("\n--- Circuit Breaker Test ---")

# Test 1: Three failures should open the breaker.
for attempt in range(1, 4):
    try:
        breaker.call(failing_service)
    except RuntimeError as error:
        print(f"Attempt {attempt}: {error}")
    print("Current state:", breaker.get_state()["state"])

assert breaker.get_state()["state"] == "OPEN"
print("\nTEST 1 PASSED: Breaker opened after three failures.")

# Test 2: Requests should be blocked while OPEN.
try:
    breaker.call(working_service)
    raise AssertionError("Expected the OPEN breaker to block the request")
except RuntimeError as error:
    if "temporarily unavailable" not in str(error):
        raise
    print("TEST 2 PASSED: Request blocked while OPEN.")

# Test 3: Wait for recovery timeout.
print("\nWaiting 11 seconds for recovery timeout...")
time.sleep(11)

# Test 4: A successful recovery attempt should close the breaker.
result = breaker.call(working_service)
print("Recovery response:", result)

assert breaker.get_state()["state"] == "CLOSED"
print("TEST 3 PASSED: HALF-OPEN recovery returned to CLOSED.")

print("\nALL CIRCUIT BREAKER TESTS PASSED.")
