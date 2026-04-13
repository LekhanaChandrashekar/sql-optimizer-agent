import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()


@contextmanager
def get_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            port=os.getenv("POSTGRES_PORT"),
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            cursor_factory=RealDictCursor,
        )
        yield conn
    finally:
        if conn:
            conn.close()


@tool
def get_all_table_names() -> list:
    """Get all table names in the public schema"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
                return [row["tablename"] for row in cur.fetchall()]
    except Exception as e:
        return []


@tool
def get_table_details(table_name: str) -> dict:
    """Get full details of a table including columns, indexes, constraints and stats"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:

                # Get columns
                cur.execute("""
                    SELECT column_name, data_type,
                           character_maximum_length,
                           is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = [dict(row) for row in cur.fetchall()]

                # Get indexes
                cur.execute("""
                    SELECT
                        i.relname AS index_name,
                        ix.indisprimary AS is_primary,
                        ix.indisunique AS is_unique,
                        array_to_string(array_agg(a.attname), ', ') AS columns,
                        pg_get_indexdef(ix.indexrelid) AS index_def,
                        s.idx_scan AS times_used
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_attribute a ON a.attrelid = t.oid
                        AND a.attnum = ANY(ix.indkey)
                    LEFT JOIN pg_stat_user_indexes s ON s.indexrelid = ix.indexrelid
                    WHERE t.relname = %s
                    GROUP BY i.relname, ix.indisprimary, ix.indisunique,
                             ix.indexrelid, s.idx_scan
                    ORDER BY i.relname
                """, (table_name,))
                indexes = [dict(row) for row in cur.fetchall()]

                # Get constraints
                cur.execute("""
                    SELECT tc.constraint_name,
                           tc.constraint_type,
                           kcu.column_name,
                           ccu.table_name AS foreign_table,
                           ccu.column_name AS foreign_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    LEFT JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.table_name = %s
                """, (table_name,))
                constraints = [dict(row) for row in cur.fetchall()]

                # Get table stats
                cur.execute("""
                    SELECT
                        n_live_tup AS live_rows,
                        n_dead_tup AS dead_rows,
                        n_mod_since_analyze AS modified_since_analyze,
                        pg_size_pretty(pg_total_relation_size(%s::regclass)) AS total_size
                    FROM pg_stat_user_tables
                    WHERE relname = %s
                """, (table_name, table_name))
                stats = dict(cur.fetchone()) if cur.rowcount > 0 else {}

                return {
                    "table_name": table_name,
                    "columns": columns,
                    "indexes": indexes,
                    "constraints": constraints,
                    "stats": stats
                }
    except Exception as e:
        return {"error": str(e)}


@tool
def get_unused_indexes() -> list:
    """Get indexes that have never been used (idx_scan = 0)"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan AS times_used,
                        pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
                    FROM pg_stat_user_indexes
                    WHERE idx_scan = 0
                    AND schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        return []


@tool
def get_tables_without_primary_keys() -> list:
    """Get tables that have no primary key"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.tablename
                    FROM pg_tables t
                    WHERE t.schemaname = 'public'
                    AND t.tablename NOT IN (
                        SELECT tc.table_name
                        FROM information_schema.table_constraints tc
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                    )
                    ORDER BY t.tablename
                """)
                return [row["tablename"] for row in cur.fetchall()]
    except Exception as e:
        return []


@tool
def get_missing_fk_indexes() -> list:
    """Get FK columns that have no index"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        tc.table_name,
                        kcu.column_name AS fk_column,
                        ccu.table_name AS references_table
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM pg_indexes pi
                        WHERE pi.tablename = tc.table_name
                        AND pi.indexdef LIKE '%' || kcu.column_name || '%'
                    )
                    ORDER BY tc.table_name
                """)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        return []


@tool
def get_table_bloat() -> list:
    """Get tables with high dead tuple ratio (bloat)"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        relname AS table_name,
                        n_live_tup AS live_rows,
                        n_dead_tup AS dead_rows,
                        CASE WHEN n_live_tup > 0
                             THEN round(100.0 * n_dead_tup / n_live_tup, 2)
                             ELSE 0
                        END AS dead_ratio_percent
                    FROM pg_stat_user_tables
                    WHERE n_dead_tup > 0
                    AND schemaname = 'public'
                    ORDER BY dead_ratio_percent DESC
                """)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        return []