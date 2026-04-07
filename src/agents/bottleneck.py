from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.tools.db_connector import (
    run_explain_analyze,
    get_table_schema,
    check_index_issues,
    check_data_type_issues,
    get_slow_queries
)
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM (Ollama - no API key needed!)
llm = ChatOllama(model="llama3.2")

# Prompt for query analysis
query_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert PostgreSQL performance analyst.

Analyze SQL query plans and detect performance bottlenecks.

Look for:
1. Seq Scan on large tables - missing index!
2. High loops count - N+1 problem!
3. High disk reads - data not in RAM!
4. Rows Removed by Filter - wasteful scanning!
5. Nested Loop on large tables - missing index on JOIN!
6. Missing LIMIT - returns too many rows!
7. Cartesian join - missing ON condition!
8. Wrong data types - type casting overhead!
9. Leading wildcard LIKE - can't use index!
10. Function on indexed column - breaks index!

For each issue provide:
- What the problem is
- Why it is slow
- Exact SQL fix

Be specific - use actual table names and column names."""),
    ("human", """Analyze this SQL query and execution plan:

SQL Query:
{query}

EXPLAIN ANALYZE Output:
{query_plan}

Identify all bottlenecks and provide specific fixes.""")
])

# Prompt for table analysis
table_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert PostgreSQL database designer.

Analyze table schema and identify ALL design issues:
1. Missing indexes on searched/JOIN columns
2. Redundant duplicate indexes
3. Wrong data types (TEXT instead of DECIMAL/INT)
4. Over-wide VARCHAR columns
5. Missing FK constraints
6. Missing NOT NULL constraints
7. Missing UNIQUE constraints
8. Low cardinality indexes
9. Missing GIN index on JSONB columns
10. Table bloat (dead tuples)

For each issue provide exact SQL fix."""),
    ("human", """Analyze this table for design issues:

Table Schema:
{schema}

Index Issues Found:
{index_issues}

Data Type Issues Found:
{data_type_issues}

Identify ALL problems and provide specific fixes.""")
])

parser = StrOutputParser()

def analyze_query(query: str) -> str:
    """Analyze a SQL query for performance bottlenecks."""
    print(f"  Running EXPLAIN ANALYZE...")
    query_plan = run_explain_analyze.invoke(query)
    print(f"  Analyzing with LLM...")
    chain = query_prompt | llm | parser
    result = chain.invoke({
        "query": query,
        "query_plan": query_plan
    })
    return result

def analyze_table(table_name: str) -> str:
    """Analyze a table for schema design issues."""
    print(f"  Getting schema...")
    schema = get_table_schema.invoke(table_name)
    index_issues = check_index_issues.invoke(table_name)
    data_type_issues = check_data_type_issues.invoke(table_name)
    print(f"  Analyzing with LLM...")
    chain = table_prompt | llm | parser
    result = chain.invoke({
        "schema": schema,
        "index_issues": index_issues,
        "data_type_issues": data_type_issues
    })
    return result

def analyze_slow_queries() -> str:
    """Get slow queries from pg_stat_statements."""
    print("  Fetching slow queries...")
    return get_slow_queries.invoke({"limit": 10})

if __name__ == "__main__":
    print("=" * 60)
    print("BOTTLENECK DETECTOR AGENT")
    print("=" * 60)

    # All bad queries to test
    bad_queries = [
        # Category 1: Index Issues
        "SELECT * FROM orders WHERE user_id = 500",
        "SELECT * FROM products WHERE attributes->>'color' = 'red'",
        "SELECT * FROM orders WHERE status = 'pending'",
        "SELECT * FROM order_items WHERE product_id = 100",
        # Category 2: Query Issues
        "SELECT * FROM users",
        "SELECT * FROM users WHERE name LIKE '%User_500%'",
        "SELECT * FROM users WHERE UPPER(email) = 'USER_500@EMAIL.COM'",
        "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10",
    ]

    # Analyze all bad queries
    for i, query in enumerate(bad_queries, 1):
        print(f"\n📊 QUERY {i}: {query[:50]}...")
        print("-" * 40)
        result = analyze_query(query)
        print(result)
        print("=" * 60)

    # Analyze all tables
    tables = ["users", "orders", "products", "order_items"]
    for table in tables:
        print(f"\n📋 TABLE: {table}")
        print("-" * 40)
        result = analyze_table(table)
        print(result)
        print("=" * 60)

    # Check pg_stat_statements
    print("\n📈 SLOW QUERIES FROM pg_stat_statements:")
    print("-" * 40)
    result = analyze_slow_queries()
    print(result)

