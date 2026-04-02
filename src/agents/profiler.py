import hashlib
from typing import Dict, Any, List

from src.tools.db_connector import run_explain, parse_execution_plan, extract_metrics
from src.tools.sql_parser import extract_metadata, detect_anti_patterns
from src.models.query_analysis import QueryIssue, IssueType, Severity
from src.tools.gorm_parser import run_gorm_parser
from src.tools.gorm_to_sql import convert_gorm_output_to_sql

# CACHE
EXPLAIN_CACHE: Dict[str, Dict] = {}

def get_query_hash(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()

# HEURISTIC ENGINE
def detect_issues(metrics: Dict, parsed_sql: Dict, plan, anti_patterns: List[str]) -> List[QueryIssue]:
    issues = []

    # FULL SCAN
    if metrics["seq_scan"] > 0:
        issues.append(QueryIssue(
            issue_type=IssueType.FULL_SCAN,
            severity=Severity.HIGH,
            description="Sequential scan detected on table",
            tables=parsed_sql.get("tables", [])
        ))

    # MISSING INDEX
    if metrics["index_scan"] == 0 and metrics["seq_scan"] > 0:
        issues.append(QueryIssue(
            issue_type=IssueType.MISSING_INDEX,
            severity=Severity.CRITICAL,
            description="No index usage detected for filtering"
        ))

    # HIGH COST
    if metrics["total_cost"] > 1000:
        issues.append(QueryIssue(
            issue_type=IssueType.HIGH_COST,
            severity=Severity.HIGH,
            description=f"High query cost detected: {metrics['total_cost']}"
        ))

    # NESTED LOOP
    if metrics["nested_loop"] > 0:
        issues.append(QueryIssue(
            issue_type=IssueType.BAD_JOIN,
            severity=Severity.HIGH,
            description="Nested loop detected — inefficient for large datasets"
        ))

    # SORT
    if metrics["sort"] > 0:
        issues.append(QueryIssue(
            issue_type=IssueType.UNINDEXED_SORT,
            severity=Severity.MEDIUM,
            description="Sort operation detected without index"
        ))

    # HASH JOIN
    if metrics["hash_join"] > 0:
        issues.append(QueryIssue(
            issue_type=IssueType.BAD_JOIN,
            severity=Severity.LOW,
            description="Hash join detected — consider merge join if sorted"
        ))

    # ANTI-PATTERNS
    for ap in anti_patterns:
        try:
            issue_type = IssueType[ap]
        except KeyError:
            issue_type = IssueType.SELECT_STAR

        issues.append(QueryIssue(
            issue_type=issue_type,
            severity=Severity.MEDIUM,
            description=f"Detected anti-pattern: {ap}"
        ))

    return issues

# CLAUDE PROMPT
SYSTEM_PROMPT = """
You are a PostgreSQL performance expert.

Understand execution plans and detect issues.

Node types:
- Seq Scan → full table scan (bad if large table)
- Index Scan → good
- Nested Loop → bad for large joins
- Hash Join → OK but depends
- Sort → expensive if no index

Heuristics:
- cost > 1000 → high
- rows > 1000 → large
- seq scan + filter → missing index

Output JSON:
[
  {
    "issue_type": "...",
    "severity": "...",
    "description": "..."
  }
]
"""
# PROFILER NODE
def profiler_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("query")
    gorm_file = state.get("gorm_file")

    # If GORM file provided, extract SQL from Go source
    if gorm_file:
        gorm_output = run_gorm_parser(gorm_file)
        sql_queries = convert_gorm_output_to_sql(gorm_output)

        if not sql_queries:
            raise ValueError("No SQL extracted from GORM file")

        query = sql_queries[0]["sql"]

    if not query:
        raise ValueError("No query provided — pass 'query' or 'gorm_file'")

    # Step 1: SQL parsing
    parsed_sql = extract_metadata(query)
    anti_patterns = detect_anti_patterns(query)

    # Step 2: caching
    qhash = get_query_hash(query)

    if qhash in EXPLAIN_CACHE:
        plan_json = EXPLAIN_CACHE[qhash]
    else:
        plan_json = run_explain(query)
        EXPLAIN_CACHE[qhash] = plan_json

    # Step 3: execution plan
    plan = parse_execution_plan(plan_json)

    # Step 4: metrics
    metrics = extract_metrics(plan)

    # Step 5: issue detection
    issues = detect_issues(metrics, parsed_sql, plan, anti_patterns)

    return {
        "parsed_sql": parsed_sql,
        "execution_plan": plan_json,
        "metrics": metrics,
        "issues": issues,
    }