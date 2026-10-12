
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "trip_db.sqlite"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rider_id INTEGER NOT NULL,
                driver_id INTEGER,
                pickup_location TEXT,
                drop_location TEXT,
                fare REAL NOT NULL,
                payment_method TEXT DEFAULT 'UPI',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def create_trip(rider_id, pickup, drop, fare, payment_method="UPI"):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO trips
            (rider_id, pickup_location, drop_location, fare, payment_method)
            VALUES (?, ?, ?, ?, ?)
        """, (rider_id, pickup, drop, fare, payment_method))
        conn.commit()
        return cursor.lastrowid


def get_trip(trip_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trips WHERE id = ?", (trip_id,)
        ).fetchone()
        return dict(row) if row else None


def update_trip(trip_id, **fields):
    allowed_fields = {
        "driver_id", "status", "payment_method", "fare"
    }
    updates = {k: v for k, v in fields.items() if k in allowed_fields}

    if not updates:
        return

    columns = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [trip_id]

    with get_connection() as conn:
        conn.execute(
            f"UPDATE trips SET {columns} WHERE id = ?", values
        )
        conn.commit()
