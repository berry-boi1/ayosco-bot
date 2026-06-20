import sqlite3
from datetime import datetime

DB_NAME = "ayosco.db"

def init_db():
    
    print("database connecting ...")
    """Creates the transactions table if it doesn't already exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            reference TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plan_data TEXT NOT NULL,
            price INTEGER NOT NULL,
            validity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    print("database connected ")
    conn.close()

def save_transaction(reference, user_id, plan):
    """Saves a new pending transaction."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (reference, user_id, plan_data, price, validity, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (reference, user_id, plan["data"], plan["price"], plan["validity"], datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_transaction(reference):
    """Fetches a transaction by reference. Returns a dict or None."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE reference = ?", (reference,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "reference": row[0],
        "user_id": row[1],
        "plan_data": row[2],
        "price": row[3],
        "validity": row[4],
        "status": row[5],
        "created_at": row[6]
    }

def mark_as_paid(reference):
    """Updates a transaction's status to 'paid'."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE transactions SET status = 'paid' WHERE reference = ?", (reference,))
    conn.commit()
    conn.close()
    
