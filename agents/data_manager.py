"""
Data Manager Agent
------------------
Handles all SQLite database operations:
  - Creating the database schema on first run
  - Saving transactions (with duplicate detection)
  - Querying transactions for the dashboard
"""

import sqlite3
import os
from datetime import datetime
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "expenses.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn


def init_db() -> None:
    """Create tables if they don't exist yet."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT    NOT NULL,
            description      TEXT    NOT NULL,
            amount           REAL    NOT NULL,
            currency         TEXT    DEFAULT 'AED',
            transaction_type TEXT    DEFAULT 'debit',
            category         TEXT    NOT NULL,
            subcategory      TEXT,
            month            TEXT    NOT NULL,
            year             INTEGER NOT NULL,
            source_file      TEXT,
            created_at       TEXT    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, description, amount)
        )
    """)
    conn.commit()
    conn.close()


def save_transactions(transactions: list[dict], source_file: str = "") -> dict:
    """
    Insert transactions into the DB, skipping duplicates.

    Returns a summary dict: {saved, skipped, total}.
    """
    init_db()
    conn = get_connection()

    saved = 0
    skipped = 0

    for tx in transactions:
        try:
            date_str = tx.get("date", "")
            # Derive month and year from the date field
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                month = dt.strftime("%B")   # e.g. "March"
                year = dt.year
            except ValueError:
                month = "Unknown"
                year = 0

            conn.execute(
                """
                INSERT INTO transactions
                    (date, description, amount, currency, transaction_type,
                     category, subcategory, month, year, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date_str,
                    tx.get("description", ""),
                    float(tx.get("amount", 0)),
                    tx.get("currency", "AED"),
                    tx.get("transaction_type", "debit"),
                    tx.get("category", "Others"),
                    tx.get("subcategory", ""),
                    month,
                    year,
                    source_file,
                ),
            )
            saved += 1
        except sqlite3.IntegrityError:
            # UNIQUE constraint — already in DB
            skipped += 1

    conn.commit()
    conn.close()

    return {"saved": saved, "skipped": skipped, "total": len(transactions)}


# ---------------------------------------------------------------------------
# Query helpers (used by dashboard)
# ---------------------------------------------------------------------------

def get_all_transactions() -> list[dict]:
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transactions_by_month(month: str, year: int) -> list[dict]:
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE month = ? AND year = ? ORDER BY date",
        (month, year),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_summary() -> list[dict]:
    """Total spend per month (debits only)."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT year, month, ROUND(SUM(amount), 2) AS total_spend,
               COUNT(*) AS num_transactions
        FROM   transactions
        WHERE  transaction_type = 'debit'
        GROUP  BY year, month
        ORDER  BY year, MIN(date)
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_summary(month: str | None = None, year: int | None = None) -> list[dict]:
    """Total spend per category, optionally filtered by month/year."""
    init_db()
    conn = get_connection()
    if month and year:
        rows = conn.execute(
            """
            SELECT category, ROUND(SUM(amount), 2) AS total,
                   COUNT(*) AS num_transactions
            FROM   transactions
            WHERE  transaction_type = 'debit'
              AND  month = ? AND year = ?
            GROUP  BY category
            ORDER  BY total DESC
            """,
            (month, year),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT category, ROUND(SUM(amount), 2) AS total,
                   COUNT(*) AS num_transactions
            FROM   transactions
            WHERE  transaction_type = 'debit'
            GROUP  BY category
            ORDER  BY total DESC
            """
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_available_months() -> list[dict]:
    """Return distinct (year, month) pairs that have data."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT year, month
        FROM   transactions
        ORDER  BY year DESC, MIN(date) DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_merchants(month: str | None = None, year: int | None = None,
                      limit: int = 10) -> list[dict]:
    """Top spending merchants."""
    init_db()
    conn = get_connection()
    if month and year:
        rows = conn.execute(
            """
            SELECT description, category,
                   ROUND(SUM(amount), 2) AS total, COUNT(*) AS visits
            FROM   transactions
            WHERE  transaction_type = 'debit'
              AND  month = ? AND year = ?
            GROUP  BY description
            ORDER  BY total DESC
            LIMIT  ?
            """,
            (month, year, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT description, category,
                   ROUND(SUM(amount), 2) AS total, COUNT(*) AS visits
            FROM   transactions
            WHERE  transaction_type = 'debit'
            GROUP  BY description
            ORDER  BY total DESC
            LIMIT  ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
