import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Railway automatically provides this when you add a PostgreSQL plugin
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    print("database connecting ...")
    """Creates the transactions table if it doesn't already exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            reference TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            plan_data TEXT NOT NULL,
            price INTEGER NOT NULL,
            validity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("database connected ")


def save_transaction(reference, user_id, plan):
    """Saves a new pending transaction."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (reference, user_id, plan_data, price, validity, status, created_at)
        VALUES (%s, %s, %s, %s, %s, 'pending', %s)
    """, (reference, user_id, plan["data"], plan["price"], plan["validity"], datetime.now().isoformat()))
    conn.commit()
    cursor.close()
    conn.close()


def get_transaction(reference):
    """Fetches a transaction by reference. Returns a dict or None."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM transactions WHERE reference = %s", (reference,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        return None

    return dict(row)


def mark_as_paid(reference):
    """Updates a transaction's status to 'paid'."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'paid' WHERE reference = %s", (reference,))
    conn.commit()
    cursor.close()
    conn.close()