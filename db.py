import os
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
        1, 20,  # min and max connections
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

    if db_pool:
        print("✅ PostgreSQL connection pool created successfully")

except Exception as e:
    print("❌ Error creating connection pool:", e)
    db_pool = None


# ---------------- GET CONNECTION ----------------
def get_connection():
    if db_pool:
        return db_pool.getconn()
    else:
        raise Exception("Database pool not initialized")


# ---------------- RETURN CONNECTION ----------------
def return_connection(conn):
    if db_pool:
        db_pool.putconn(conn)


# ---------------- CLOSE POOL ----------------
def close_all_connections():
    if db_pool:
        db_pool.closeall()
        print("🔒 All DB connections closed")