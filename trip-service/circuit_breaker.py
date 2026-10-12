
import time
import threading


class CircuitBreaker:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF-OPEN"

    def __init__(self, failure_threshold=3, recovery_timeout=10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.state = self.CLOSED
        self.last_failure_time = None
        self.lock = threading.Lock()

    def call(self, function, *args, **kwargs):
        with self.lock:
            if self.state == self.OPEN:
                elapsed = time.monotonic() - self.last_failure_time

                if elapsed >= self.recovery_timeout:
                    self.state = self.HALF_OPEN
                    print("Circuit Breaker: OPEN -> HALF-OPEN")
                else:
                    raise RuntimeError(
                        "Circuit Breaker is OPEN. "
                        "Service temporarily unavailable."
                    )

            trial_request = self.state == self.HALF_OPEN

        try:
            result = function(*args, **kwargs)

            with self.lock:
                if self.state == self.HALF_OPEN:
                    self.state = self.CLOSED
                    print("Circuit Breaker: HALF-OPEN -> CLOSED")

                self.failure_count = 0
                self.last_failure_time = None

            return result

        except Exception:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.monotonic()

                if self.state == self.HALF_OPEN:
                    self.state = self.OPEN
                    print("Circuit Breaker: HALF-OPEN -> OPEN")

                elif (
                    self.state == self.CLOSED
                    and self.failure_count >= self.failure_threshold
                ):
                    self.state = self.OPEN
                    print("Circuit Breaker: CLOSED -> OPEN")

            raise

    def get_state(self):
        with self.lock:
            return {
                "state": self.state,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
            }
