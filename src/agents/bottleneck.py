import logging
import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel
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

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)

# Constants
MODEL_NAME = "gemma3"
DEFAULT_SLOW_QUERY_LIMIT = 10


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class IssueType(str, Enum):
    FULL_SCAN = "FULL_SCAN"
    MISSING_INDEX = "MISSING_INDEX"
    N_PLUS_ONE = "N_PLUS_ONE"
    LOCK_CONTENTION = "LOCK_CONTENTION"
    INEFFICIENT_PAGINATION = "INEFFICIENT_PAGINATION"
    SORT_WITHOUT_INDEX = "SORT_WITHOUT_INDEX"
    MISSING_PARTIAL_INDEX = "MISSING_PARTIAL_INDEX"
    SCHEMA_ISSUE = "SCHEMA_ISSUE"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class QueryIssue(BaseModel):
    issue_type: IssueType
    severity: Severity
    category: str = "scalability"
    description: str
    affected_table: Optional[str] = None
    suggestion: str


class QueryInput(BaseModel):
    sql: str
    source_file: Optional[str] = None
    context: Optional[str] = None


class ExecutionPlan(BaseModel):
    raw_plan: str
    total_cost: Optional[float] = None
    has_seq_scan: bool = False
    has_index_scan: bool = False


class AnalysisState(BaseModel):
    query_input: QueryInput
    execution_plan: Optional[ExecutionPlan] = None
    bottleneck_issues: list[QueryIssue] = []


# ─────────────────────────────────────────────
# LLM Setup
# ─────────────────────────────────────────────

def get_llm() -> ChatOllama:
    """Initialize and return the LLM instance."""
    return ChatOllama(model=MODEL_NAME)


# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────

scalability_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert PostgreSQL scalability analyst.

Detect patterns that degrade under load. For each issue found, output in this EXACT format:

ISSUE_TYPE: <one of: FULL_SCAN, MISSING_INDEX, N_PLUS_ONE, LOCK_CONTENTION, INEFFICIENT_PAGINATION, SORT_WITHOUT_INDEX, MISSING_PARTIAL_INDEX>
SEVERITY: <one of: critical, warning, info>
AFFECTED_TABLE: <table name or "unknown">
DESCRIPTION: <what the problem is and why it degrades under load>
SUGGESTION: <exact SQL fix or code change>
---

Detect these scalability patterns:
1. FULL_SCAN: Sequential scans on tables with no row-count bound
2. MISSING_INDEX: Queries filtering/joining on unindexed columns
3. N_PLUS_ONE: Repeated similar queries in loops (from GORM parser output)
4. LOCK_CONTENTION: UPDATE/DELETE touching many rows without proper WHERE clause
5. INEFFICIENT_PAGINATION: OFFSET-based pagination on large datasets (suggest keyset pagination)
6. SORT_WITHOUT_INDEX: ORDER BY on non-indexed columns with LIMIT
7. MISSING_PARTIAL_INDEX: Queries filtering on low-cardinality status columns without partial indexes

Be specific — use actual table names and column names from the query."""),
    ("human", """Analyze this SQL query and execution plan for scalability issues:

SQL Query:
{query}

EXPLAIN ANALYZE Output:
{query_plan}

Identify ALL scalability bottlenecks.""")
])

table_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert PostgreSQL database designer.

Analyze table schema and identify ALL design issues. For each issue found, output in this EXACT format:

ISSUE_TYPE: <one of: MISSING_INDEX, SCHEMA_ISSUE, MISSING_PARTIAL_INDEX>
SEVERITY: <one of: critical, warning, info>
AFFECTED_TABLE: <table name>
DESCRIPTION: <what the problem is>
SUGGESTION: <exact SQL fix>
---

Look for:
1. Missing indexes on searched/JOIN columns
2. Redundant duplicate indexes
3. Wrong data types (TEXT instead of DECIMAL/INT)
4. Missing partial indexes on status/low-cardinality columns
5. Missing FK constraints
6. Missing NOT NULL constraints
7. Missing GIN index on JSONB columns"""),
    ("human", """Analyze this table for design issues:

Table Schema:
{schema}

Index Issues Found:
{index_issues}

Data Type Issues Found:
{data_type_issues}

Identify ALL problems.""")
])

parser = StrOutputParser()


# ─────────────────────────────────────────────
# Static Pattern Detection (no LLM needed)
# ─────────────────────────────────────────────

def detect_static_patterns(query: str) -> list[QueryIssue]:
    """Detect scalability issues statically without LLM."""
    issues = []
    query_upper = query.upper()

    # Detect OFFSET pagination
    if re.search(r'\bOFFSET\b', query_upper):
        issues.append(QueryIssue(
            issue_type=IssueType.INEFFICIENT_PAGINATION,
            severity=Severity.WARNING,
            category="scalability",
            description="OFFSET-based pagination degrades as dataset grows — full table scan up to OFFSET row.",
            affected_table=_extract_table(query),
            suggestion="Replace OFFSET/LIMIT with keyset pagination: WHERE id > :last_seen_id ORDER BY id LIMIT n"
        ))

    # Detect UPDATE/DELETE without WHERE
    if re.search(r'\b(UPDATE|DELETE)\b', query_upper) and 'WHERE' not in query_upper:
        issues.append(QueryIssue(
            issue_type=IssueType.LOCK_CONTENTION,
            severity=Severity.CRITICAL,
            category="scalability",
            description="UPDATE/DELETE without WHERE clause touches ALL rows — causes full table lock contention.",
            affected_table=_extract_table(query),
            suggestion="Add a WHERE clause to limit affected rows and reduce lock scope."
        ))

    # Detect SELECT * (over-fetching)
    if re.search(r'SELECT\s+\*', query_upper):
        issues.append(QueryIssue(
            issue_type=IssueType.FULL_SCAN,
            severity=Severity.INFO,
            category="scalability",
            description="SELECT * fetches all columns — increases memory and network overhead under load.",
            affected_table=_extract_table(query),
            suggestion="Replace SELECT * with specific column names needed by the application."
        ))

    # Detect leading wildcard LIKE
    if re.search(r"LIKE\s+'%", query_upper):
        issues.append(QueryIssue(
            issue_type=IssueType.MISSING_INDEX,
            severity=Severity.WARNING,
            category="scalability",
            description="Leading wildcard LIKE '%...' cannot use B-tree indexes — causes full table scan.",
            affected_table=_extract_table(query),
            suggestion="Use a GIN index with pg_trgm: CREATE INDEX USING gin(column gin_trgm_ops);"
        ))

    # Detect function on column in WHERE
    if re.search(r'WHERE\s+\w+\s*\(', query_upper):
        issues.append(QueryIssue(
            issue_type=IssueType.MISSING_INDEX,
            severity=Severity.WARNING,
            category="scalability",
            description="Function applied on column in WHERE clause breaks index usage.",
            affected_table=_extract_table(query),
            suggestion="Create a functional index: CREATE INDEX ON table (function(column));"
        ))

    return issues


def _extract_table(query: str) -> Optional[str]:
    """Extract the main table name from a SQL query."""
    match = re.search(r'\bFROM\s+(\w+)', query, re.IGNORECASE)
    if not match:
        match = re.search(r'\b(UPDATE|DELETE FROM|INSERT INTO)\s+(\w+)', query, re.IGNORECASE)
        if match:
            return match.group(2)
    return match.group(1) if match else None


# ─────────────────────────────────────────────
# LLM-based Issue Parsing
# ─────────────────────────────────────────────

def parse_llm_issues(llm_output: str, category: str = "scalability") -> list[QueryIssue]:
    """Parse structured LLM output into QueryIssue objects."""
    issues = []
    blocks = llm_output.strip().split("---")

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            def extract(field):
                match = re.search(rf'{field}:\s*(.+)', block)
                return match.group(1).strip() if match else ""

            issue_type_str = extract("ISSUE_TYPE").upper()
            severity_str = extract("SEVERITY").lower()
            affected_table = extract("AFFECTED_TABLE") or None
            description = extract("DESCRIPTION")
            suggestion = extract("SUGGESTION")

            if not description:
                continue

            issue_type = IssueType(issue_type_str) if issue_type_str in IssueType._value2member_map_ else IssueType.UNKNOWN
            severity = Severity(severity_str) if severity_str in Severity._value2member_map_ else Severity.WARNING

            issues.append(QueryIssue(
                issue_type=issue_type,
                severity=severity,
                category=category,
                description=description,
                affected_table=affected_table if affected_table != "unknown" else None,
                suggestion=suggestion
            ))
        except Exception as e:
            logger.warning(f"Failed to parse issue block: {e}")
            continue

    return issues


# ─────────────────────────────────────────────
# Core Analysis Functions
# ─────────────────────────────────────────────

def analyze_query(query: str, execution_plan: Optional[str] = None) -> list[QueryIssue]:
    """Analyze a SQL query for scalability bottlenecks."""
    try:
        # Step 1: Static pattern detection (fast, no LLM)
        issues = detect_static_patterns(query)

        # Step 2: Get execution plan if not provided
        if not execution_plan:
            execution_plan = run_explain_analyze.invoke(query)

        # Step 3: LLM-based deep analysis
        chain = scalability_prompt | get_llm() | parser
        llm_output = chain.invoke({
            "query": query,
            "query_plan": execution_plan
        })

        # Step 4: Parse LLM output into QueryIssue objects
        llm_issues = parse_llm_issues(llm_output, category="scalability")
        issues.extend(llm_issues)

        return issues

    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return [QueryIssue(
            issue_type=IssueType.UNKNOWN,
            severity=Severity.WARNING,
            category="scalability",
            description=f"Analysis failed: {e}",
            suggestion="Check database connection and query syntax."
        )]


def analyze_table(table_name: str) -> list[QueryIssue]:
    """Analyze a table for schema design issues."""
    try:
        schema = get_table_schema.invoke(table_name)
        index_issues = check_index_issues.invoke(table_name)
        data_type_issues = check_data_type_issues.invoke(table_name)

        chain = table_prompt | get_llm() | parser
        llm_output = chain.invoke({
            "schema": schema,
            "index_issues": index_issues,
            "data_type_issues": data_type_issues
        })

        return parse_llm_issues(llm_output, category="schema")

    except Exception as e:
        logger.error(f"Error analyzing table {table_name}: {e}")
        return [QueryIssue(
            issue_type=IssueType.UNKNOWN,
            severity=Severity.WARNING,
            category="schema",
            description=f"Table analysis failed: {e}",
            affected_table=table_name,
            suggestion="Check database connection."
        )]


def analyze_slow_queries(limit: int = DEFAULT_SLOW_QUERY_LIMIT) -> str:
    """Get slow queries from pg_stat_statements."""
    try:
        return get_slow_queries.invoke({"limit": limit})
    except Exception as e:
        logger.error(f"Error fetching slow queries: {e}")
        return f"Error fetching slow queries: {e}"


# ─────────────────────────────────────────────
# LangGraph Node
# ─────────────────────────────────────────────

def bottleneck_detector_node(state: AnalysisState) -> AnalysisState:
    """
    LangGraph node for bottleneck detection.
    Input:  AnalysisState with query_input + optional execution_plan
    Output: AnalysisState with bottleneck_issues populated
    """
    query = state.query_input.sql
    execution_plan = state.execution_plan.raw_plan if state.execution_plan else None

    issues = analyze_query(query, execution_plan)
    state.bottleneck_issues = issues
    return state


# ─────────────────────────────────────────────
# Standalone Runner (for testing)
# ─────────────────────────────────────────────

def _print_issues(issues: list[QueryIssue]):
    """Pretty print QueryIssue objects."""
    if not issues:
        print("  No issues found.")
        return
    for issue in issues:
        icon = "[CRITICAL]" if issue.severity == Severity.CRITICAL else "[WARNING]" if issue.severity == Severity.WARNING else "[INFO]"
        print(f"  {icon} {issue.issue_type}")
        print(f"     Table    : {issue.affected_table or 'N/A'}")
        print(f"     Problem  : {issue.description}")
        print(f"     Fix      : {issue.suggestion}")
        print()


if __name__ == "__main__":
    load_dotenv()

    print("=" * 60)
    print("BOTTLENECK DETECTOR AGENT")
    print("=" * 60)

    bad_queries = [
        "SELECT * FROM orders WHERE user_id = 500",
        "SELECT * FROM products WHERE attributes->>'color' = 'red'",
        "SELECT * FROM orders WHERE status = 'pending'",
        "SELECT * FROM order_items WHERE product_id = 100",
        "SELECT * FROM users",
        "SELECT * FROM users WHERE name LIKE '%User_500%'",
        "SELECT * FROM users WHERE UPPER(email) = 'USER_500@EMAIL.COM'",
        "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10",
        "SELECT * FROM orders LIMIT 10 OFFSET 50000",           # OFFSET pagination
        "DELETE FROM orders",                                    # No WHERE clause
    ]

    for i, query in enumerate(bad_queries, 1):
        print(f"\n QUERY {i}: {query[:60]}...")
        print("-" * 40)

        # Use as LangGraph node
        state = AnalysisState(query_input=QueryInput(sql=query))
        result_state = bottleneck_detector_node(state)
        _print_issues(result_state.bottleneck_issues)
        print("=" * 60)

    # Analyze tables
    tables = ["users", "orders", "products", "order_items"]
    for table in tables:
        print(f"\n TABLE: {table}")
        print("-" * 40)
        issues = analyze_table(table)
        _print_issues(issues)
        print("=" * 60)

    # Slow queries
    print("\n SLOW QUERIES FROM pg_stat_statements:")
    print("-" * 40)
    print(analyze_slow_queries())


