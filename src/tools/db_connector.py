import psycopg2
import os
from dotenv import load_dotenv
from langchain_core.tools import tool
 
load_dotenv()
 
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        database=os.getenv("DB_NAME", "testdb"),
        user=os.getenv("DB_USER", "optimizer"),
        password=os.getenv("DB_PASSWORD", "optimizer123")
    )
 
@tool
def run_explain_analyze(query: str) -> str:
    """Run EXPLAIN ANALYZE on a SQL query and return the query plan"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN ANALYZE {query}")
        rows = cursor.fetchall()
        return "\n".join([row[0] for row in rows])
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()
 
@tool
def get_table_schema(table_name: str) -> str:
    """Get schema of a table including columns, types, indexes and constraints"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
 
        # Get columns
        cursor.execute("""
            SELECT column_name, data_type,
                   character_maximum_length,
                   is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = cursor.fetchall()
 
        # Get indexes
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = %s
        """, (table_name,))
        indexes = cursor.fetchall()
 
        # Get constraints
        cursor.execute("""
            SELECT tc.constraint_name, tc.constraint_type,
                   kcu.column_name, ccu.table_name AS foreign_table,
                   ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            LEFT JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = %s
        """, (table_name,))
        constraints = cursor.fetchall()
 
        # Build result
        result = f"Table: {table_name}\n\nColumns:\n"
        for col in columns:
            result += f"  {col[0]} → {col[1]}"
            if col[2]:
                result += f"({col[2]})"
            result += f" | nullable: {col[3]}"
            if col[4]:
                result += f" | default: {col[4]}"
            result += "\n"
 
        result += "\nIndexes:\n"
        if indexes:
            for idx in indexes:
                result += f"  {idx[0]}: {idx[1]}\n"
        else:
            result += "  NO INDEXES FOUND! \n"
 
        result += "\nConstraints:\n"
        if constraints:
            for con in constraints:
                result += f"  {con[1]}: {con[2]}"
                if con[3]:
                    result += f" → {con[3]}.{con[4]}"
                result += "\n"
        else:
            result += "  NO CONSTRAINTS FOUND! \n"
 
        return result
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()
 
@tool
def get_all_tables() -> str:
    """Get list of all tables in the database with their sizes"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tablename,
                   pg_size_pretty(pg_total_relation_size(tablename::regclass))
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(tablename::regclass) DESC
        """)
        tables = cursor.fetchall()
        result = "Tables in database:\n"
        for table in tables:
            result += f"  {table[0]} → size: {table[1]}\n"
        return result
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()
 
@tool
def check_index_issues(table_name: str) -> str:
    """Check for index issues including redundant, missing and low cardinality indexes"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
 
        # Get indexes
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = %s
            ORDER BY indexdef
        """, (table_name,))
        indexes = cursor.fetchall()
 
        # Get table stats
        cursor.execute("""
            SELECT n_live_tup, n_dead_tup
            FROM pg_stat_user_tables
            WHERE relname = %s
        """, (table_name,))
        stats = cursor.fetchone()
 
        issues = f"Index Issues for {table_name}:\n"
 
        # Find redundant indexes
        seen = {}
        for idx in indexes:
            if idx[1] in seen:
                issues += f"  REDUNDANT INDEX: {idx[0]} duplicates {seen[idx[1]]}\n"
                issues += f"     Fix: DROP INDEX {idx[0]};\n"
            else:
                seen[idx[1]] = idx[0]
 
        # Check table bloat
        if stats:
            live, dead = stats
            if dead and live and dead > live * 0.1:
                issues += f"  TABLE BLOAT: {dead} dead tuples vs {live} live!\n"
                issues += f"     Fix: VACUUM ANALYZE {table_name};\n"
 
        return issues
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()
 
@tool
def check_data_type_issues(table_name: str) -> str:
    """Check for wrong data types in a table"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = cursor.fetchall()
 
        issues = f"Data Type Issues for {table_name}:\n"
        found = False
 
        for col in columns:
            name, dtype, max_len = col
 
            # Price/amount as TEXT
            if any(x in name.lower() for x in ['price', 'amount', 'cost']):
                if dtype == 'text':
                    issues += f"  {name} is TEXT → should be DECIMAL!\n"
                    found = True
 
            # Stock/quantity as TEXT
            if any(x in name.lower() for x in ['stock', 'quantity']):
                if dtype == 'text':
                    issues += f"   {name} is TEXT → should be INT!\n"
                    found = True
 
            # Phone as INT
            if 'phone' in name.lower() and dtype == 'integer':
                issues += f"   {name} is INT → should be VARCHAR!\n"
                found = True
 
            # Over-wide VARCHAR
            if dtype == 'character varying' and max_len and max_len > 500:
                issues += f"   {name} is VARCHAR({max_len}) → too wide!\n"
                found = True
 
        if not found:
            issues += "   No data type issues found!\n"
 
        return issues
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()
@tool
def get_slow_queries(limit: int = 10) -> str:
    """Get top slowest queries from pg_stat_statements extension"""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Check if pg_stat_statements is enabled
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension
                WHERE extname = 'pg_stat_statements'
            );
        """)
        enabled = cursor.fetchone()[0]

        if not enabled:
            return """pg_stat_statements not enabled!
To enable:
1. Add to postgresql.conf:
   shared_preload_libraries = 'pg_stat_statements'
2. Restart Postgres
3. Run: CREATE EXTENSION pg_stat_statements;"""

        cursor.execute("""
            SELECT query, calls, mean_exec_time,
                   total_exec_time, rows
            FROM pg_stat_statements
            ORDER BY mean_exec_time DESC
            LIMIT %s
        """, (limit,))
        queries = cursor.fetchall()

        if not queries:
            return "No queries in pg_stat_statements yet!"

        result = f"Top {limit} Slowest Queries:\n\n"
        for i, q in enumerate(queries, 1):
            result += f"{i}. Query: {q[0][:100]}\n"
            result += f"   Calls: {q[1]}\n"
            result += f"   Avg time: {q[2]:.2f}ms\n"
            result += f"   Total time: {q[3]:.2f}ms\n\n"

        return result
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        conn.close()