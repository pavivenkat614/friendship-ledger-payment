import os
import pandas as pd
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

# ---------------- LOAD ENV ----------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", "5432")

# ---------------- VALIDATION ----------------
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASS]):
    raise ValueError("Missing database environment variables. Check your .env file.")

# ---------------- CONNECTION POOL ----------------
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1,
        20,
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
    )
    print("✅ PostgreSQL connection pool created successfully")
except Exception as e:
    print("❌ Error creating connection pool:", e)
    db_pool = None


# ---------------- CONNECTION HELPERS ----------------
def get_connection():
    if db_pool:
        return db_pool.getconn()
    raise Exception("Database pool not initialized")


def return_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)


def close_all_connections():
    if db_pool:
        db_pool.closeall()
        print("🔒 All DB connections closed")


# ---------------- USER FUNCTIONS ----------------
def register_user(username, email, password):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
            """,
            (username, email, password),
        )
        conn.commit()
        return True
    except Exception as e:
        print("register_user error:", e)
        conn.rollback()
        return False
    finally:
        cur.close()
        return_connection(conn)


def login_user(username_or_email, password):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id
            FROM users
            WHERE (username = %s OR email = %s)
              AND password = %s
            """,
            (username_or_email, username_or_email, password),
        )
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        print("login_user error:", e)
        return None
    finally:
        cur.close()
        return_connection(conn)


# ---------------- GROUP FUNCTIONS ----------------
def get_user_groups(user_id):
    conn = get_connection()
    try:
        query = "SELECT id, name FROM groups WHERE user_id = %s ORDER BY id"
        return pd.read_sql(query, conn, params=(user_id,))
    except Exception as e:
        print("get_user_groups error:", e)
        return pd.DataFrame(columns=["id", "name"])
    finally:
        return_connection(conn)


# ---------------- FRIEND FUNCTIONS ----------------
def add_friend(user_id, group_id, name, upi_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO friends (user_id, group_id, name, upi_id)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, group_id, name, upi_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print("add_friend error:", e)
        conn.rollback()
        return False
    finally:
        cur.close()
        return_connection(conn)


def get_friends(user_id, group_id):
    conn = get_connection()
    try:
        query = """
        SELECT id, name, upi_id
        FROM friends
        WHERE user_id = %s AND group_id = %s
        ORDER BY id
        """
        return pd.read_sql(query, conn, params=(user_id, group_id))
    except Exception as e:
        print("get_friends error:", e)
        return pd.DataFrame(columns=["id", "name", "upi_id"])
    finally:
        return_connection(conn)


# ---------------- EXPENSE FUNCTIONS ----------------
def add_expense(user_id, group_id, expense_date, description, paid_by, amount, split_ids):
    conn = get_connection()
    cur = conn.cursor()
    try:
        split_names = []
        for fid in split_ids:
            cur.execute("SELECT name FROM friends WHERE id = %s", (fid,))
            row = cur.fetchone()
            if row:
                split_names.append(row[0])

        split_string = ",".join(split_names)

        cur.execute(
            """
            INSERT INTO expenses
            (user_id, group_id, expense_date, description, paid_by, amount, splits)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, group_id, expense_date, description, paid_by, amount, split_string),
        )
        conn.commit()
        return True
    except Exception as e:
        print("add_expense error:", e)
        conn.rollback()
        return False
    finally:
        cur.close()
        return_connection(conn)


def get_expenses(user_id, group_id):
    conn = get_connection()
    try:
        query = """
        SELECT e.id,
               e.description,
               e.amount,
               f.name AS paid_by,
               e.splits
        FROM expenses e
        LEFT JOIN friends f ON e.paid_by = f.id
        WHERE e.user_id = %s AND e.group_id = %s
        ORDER BY e.id DESC
        """
        return pd.read_sql(query, conn, params=(user_id, group_id))
    except Exception as e:
        print("get_expenses error:", e)
        return pd.DataFrame(columns=["id", "description", "amount", "paid_by", "splits"])
    finally:
        return_connection(conn)


# ---------------- PAYMENT FUNCTIONS ----------------
def get_payments(group_id):
    conn = get_connection()
    try:
        query = """
        SELECT id, payer, receiver, amount, status
        FROM payments
        WHERE group_id = %s
        ORDER BY id DESC
        """
        return pd.read_sql(query, conn, params=(group_id,))
    except Exception as e:
        print("get_payments error:", e)
        return pd.DataFrame(columns=["id", "payer", "receiver", "amount", "status"])
    finally:
        return_connection(conn)


def mark_payment_paid(payment_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE payments
            SET status = 'PAID'
            WHERE id = %s
            """,
            (payment_id,),
        )
        conn.commit()
        return True
    except Exception as e:
        print("mark_payment_paid error:", e)
        conn.rollback()
        return False
    finally:
        cur.close()
        return_connection(conn)
