"""
Database initialization script using raw psycopg2 (per lab requirements).
Verifies connection to PostgreSQL and optionally creates the database if missing.
"""
import os
import sys
import time

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "charity")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def ensure_database_exists():
    """Connect to postgres, create charity db if it does not exist."""
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (DB_NAME,),
        )
        if cur.fetchone() is None:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"Database {DB_NAME} created")
    conn.close()


def verify_connection():
    """Verify connection to the charity database."""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    conn.close()
    print("Database connection verified")


def main():
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            ensure_database_exists()
            verify_connection()
            return
        except psycopg2.OperationalError as e:
            print(f"Waiting for database... ({attempt + 1}/{max_attempts}): {e}")
            time.sleep(2)
    print("Could not connect to database")
    sys.exit(1)


if __name__ == "__main__":
    main()
