import psycopg2
import os
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from langchain_core.tools import tool
from src.models.query_analysis import ExecutionPlan, ExecutionNode

load_dotenv()
class DatabaseError(Exception):
    pass
def validate_query(query: str):
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    q = query.strip().lower()

    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate"]

    if any(q.startswith(cmd) for cmd in forbidden):
        raise ValueError("Only SELECT queries allowed")

    if ";" in query.strip()[:-1]:
        raise ValueError("Multiple statements not allowed")
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
    except Exception as e:
        raise DatabaseError(f"DB connection failed: {e}")
    finally:
        if conn:
            conn.close()


@tool
def run_explain(query: str) -> dict:
    """Run EXPLAIN ANALYZE on a SQL query and return the execution plan as JSON"""
    validate_query(query)

    explain_analyze = f"""
    EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
    {query}
    """

    explain_only = f"""
    EXPLAIN (FORMAT JSON)
    {query}
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = 5000;")

                try:
                    # Try ANALYZE first
                    cur.execute(explain_analyze)
                    result = cur.fetchone()

                except Exception:
                    # FALLBACK to safe EXPLAIN
                    conn.rollback()
                    cur.execute(explain_only)
                    result = cur.fetchone()

                if not result:
                    raise DatabaseError("Empty EXPLAIN result")

                plan_json = result.get("QUERY PLAN")

                if not plan_json:
                    raise DatabaseError("Invalid EXPLAIN format")

                return plan_json[0]

    except Exception as e:
        raise DatabaseError(f"EXPLAIN failed: {e}")


def parse_execution_plan(plan_json: dict) -> ExecutionPlan:
    plan_root = plan_json.get("Plan", {})
    execution_time = plan_json.get("Execution Time", 0)

    nodes = []

    def traverse(node):
        nodes.append(
            ExecutionNode(
                node_type=node.get("Node Type"),
                total_cost=node.get("Total Cost", 0),
                plan_rows=node.get("Plan Rows", 0),
                plan_width=node.get("Plan Width", 0),
                actual_time=node.get("Actual Total Time", 0),
                loops=node.get("Actual Loops", 0),
                relation_name=node.get("Relation Name"),
            )
        )
        for child in node.get("Plans", []):
            traverse(child)

    traverse(plan_root)

    return ExecutionPlan(
        total_cost=plan_root.get("Total Cost", 0),
        execution_time=execution_time,
        nodes=nodes,
    )


def extract_metrics(plan: ExecutionPlan):
    metrics = {
        "seq_scan": 0,
        "index_scan": 0,
        "bitmap_scan": 0,
        "sort": 0,
        "hash_join": 0,
        "nested_loop": 0,
        "total_cost": plan.total_cost,
        "execution_time": plan.execution_time,
    }

    for node in plan.nodes:
       nt = node.node_type or ""

      if nt == "Seq Scan":
          metrics["seq_scan"] += 1
      elif nt in ["Index Scan", "Index Only Scan"]:
          metrics["index_scan"] += 1
      elif "Bitmap" in nt:
          metrics["bitmap_scan"] += 1
      elif nt == "Sort":
          metrics["sort"] += 1
      elif "Hash Join" in nt:
          metrics["hash_join"] += 1
      elif "Nested Loop" in nt:
          metrics["nested_loop"] += 1

    return metrics

# Schema inspection tools

@tool
def get_table_schema(table_name: str) -> str:
    """Get schema of a table including columns, types, indexes and constraints"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type,
                           character_maximum_length,
                           is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = cur.fetchall()

                cur.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = %s
                """, (table_name,))
                indexes = cur.fetchall()

                cur.execute("""
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
                constraints = cur.fetchall()

                result = f"Table: {table_name}\n\nColumns:\n"
                for col in columns:
                    result += f"  {col['column_name']} -> {col['data_type']}"
                    if col["character_maximum_length"]:
                        result += f"({col['character_maximum_length']})"
                    result += f" | nullable: {col['is_nullable']}"
                    if col["column_default"]:
                        result += f" | default: {col['column_default']}"
                    result += "\n"

                result += "\nIndexes:\n"
                if indexes:
                    for idx in indexes:
                        result += f"  {idx['indexname']}: {idx['indexdef']}\n"
                else:
                    result += "  NO INDEXES FOUND!\n"

                result += "\nConstraints:\n"
                if constraints:
                    for con in constraints:
                        result += f"  {con['constraint_type']}: {con['column_name']}"
                        if con["foreign_table"]:
                            result += f" -> {con['foreign_table']}.{con['foreign_column']}"
                        result += "\n"
                else:
                    result += "  NO CONSTRAINTS FOUND!\n"

                return result

    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_all_tables() -> str:
    """Get list of all tables in the database with their sizes"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tablename,
                           pg_size_pretty(pg_total_relation_size(tablename::regclass))
                               AS total_size
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(tablename::regclass) DESC
                """)
                tables = cur.fetchall()

                result = "Tables in database:\n"
                for table in tables:
                    result += f"  {table['tablename']} -> size: {table['total_size']}\n"
                return result

    except Exception as e:
        return f"Error: {str(e)}"


@tool
def check_index_issues(table_name: str) -> str:
    """Check for index issues including redundant, missing and low cardinality indexes"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = %s
                    ORDER BY indexdef
                """, (table_name,))
                indexes = cur.fetchall()

                cur.execute("""
                    SELECT n_live_tup, n_dead_tup
                    FROM pg_stat_user_tables
                    WHERE relname = %s
                """, (table_name,))
                stats = cur.fetchone()

                issues = f"Index Issues for {table_name}:\n"
                found = False

                seen = {}
                for idx in indexes:
                    defn = idx["indexdef"]
                    if defn in seen:
                        issues += f"  REDUNDANT: {idx['indexname']} duplicates {seen[defn]}\n"
                        issues += f"    Fix: DROP INDEX {idx['indexname']};\n"
                        found = True
                    else:
                        seen[defn] = idx["indexname"]

                if stats:
                    live = stats["n_live_tup"] or 0
                    dead = stats["n_dead_tup"] or 0
                    if dead > 0 and live > 0 and dead > live * 0.1:
                        issues += f"  BLOAT: {dead} dead tuples vs {live} live\n"
                        issues += f"    Fix: VACUUM ANALYZE {table_name};\n"
                        found = True

                if not found:
                    issues += "  No index issues found.\n"

                return issues

    except Exception as e:
        return f"Error: {str(e)}"


@tool
def check_data_type_issues(table_name: str) -> str:
    """Check for wrong data types in a table"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = cur.fetchall()

                issues = f"Data Type Issues for {table_name}:\n"
                found = False

                for col in columns:
                    name = col["column_name"]
                    dtype = col["data_type"]
                    max_len = col["character_maximum_length"]

                    if any(x in name.lower() for x in ["price", "amount", "cost"]):
                        if dtype == "text":
                            issues += f"  {name} is TEXT -> should be DECIMAL\n"
                            found = True

                    if any(x in name.lower() for x in ["stock", "quantity"]):
                        if dtype == "text":
                            issues += f"  {name} is TEXT -> should be INT\n"
                            found = True

                    if "phone" in name.lower() and dtype == "integer":
                        issues += f"  {name} is INT -> should be VARCHAR\n"
                        found = True

                    if dtype == "character varying" and max_len and max_len > 500:
                        issues += f"  {name} is VARCHAR({max_len}) -> too wide\n"
                        found = True

                if not found:
                    issues += "  No data type issues found.\n"

                return issues

    except Exception as e:
        return f"Error: {str(e)}"
