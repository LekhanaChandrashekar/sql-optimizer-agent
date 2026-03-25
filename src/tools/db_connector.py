import os
import psycopg2

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "sql_optimizer"),
        user=os.getenv("POSTGRES_USER", "y"),
        password=os.getenv("POSTGRES_PASSWORD")
    )