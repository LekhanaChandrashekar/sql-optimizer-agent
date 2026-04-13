from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List
from dotenv import load_dotenv
import json
import re

from src.models.query_analysis import QueryIssue, IssueType, Severity
from src.tools.schema_reader import (
    get_all_table_names,
    get_table_details,
    get_unused_indexes,
    get_tables_without_primary_keys,
    get_missing_fk_indexes,
    get_table_bloat
)

load_dotenv()

# Initialize LLM
llm = ChatOllama(model="gemma3")
parser = StrOutputParser()

# System prompt for schema analysis
schema_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert PostgreSQL database designer.

Analyze the table schema and detect ALL design issues.

For each issue output EXACTLY in this format:
ISSUE_TYPE: <type>
SEVERITY: <critical/high/medium/low>
TABLE: <table_name>
DESCRIPTION: <what is wrong>
SUGGESTION: <exact SQL fix>
---

Issue types to detect:
- MISSING_INDEX: no index on FK or searched columns
- FULL_SCAN: table has no indexes at all
- REDUNDANT_INDEX: duplicate or prefix indexes
- UNUSED_INDEX: index never used (idx_scan = 0)
- WRONG_DATA_TYPE: TEXT instead of DECIMAL/INT/VARCHAR
- MISSING_FK: FK relationship without constraint
- TABLE_BLOAT: too many dead tuples
- OVER_INDEXED: too many indexes on one table
- MISSING_PK: table has no primary key
- LOW_CARDINALITY_INDEX: index on low cardinality column

Be specific - use actual table names and column names!"""),
    ("human", """Analyze this table schema for design issues:

Table Details:
{table_details}

Unused Indexes:
{unused_indexes}

Tables Without Primary Keys:
{tables_without_pks}

Missing FK Indexes:
{missing_fk_indexes}

Table Bloat:
{table_bloat}

Find ALL design issues and provide specific SQL fixes!""")
])


def parse_llm_issues(llm_output: str, table_name: str) -> List[QueryIssue]:
    """Parse LLM output into QueryIssue objects"""
    issues = []

    blocks = llm_output.split("---")

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        try:
            issue_type_match = re.search(r'ISSUE_TYPE:\s*(\w+)', block)
            severity_match = re.search(r'SEVERITY:\s*(\w+)', block)
            description_match = re.search(r'DESCRIPTION:\s*(.+?)(?=SUGGESTION:|$)', block, re.DOTALL)
            suggestion_match = re.search(r'SUGGESTION:\s*(.+?)$', block, re.DOTALL)

            if not issue_type_match:
                continue

            issue_type_str = issue_type_match.group(1).upper()
            severity_str = severity_match.group(1).upper() if severity_match else "MEDIUM"
            description = description_match.group(1).strip() if description_match else ""
            suggestion = suggestion_match.group(1).strip() if suggestion_match else ""

            issue_type_map = {
                "MISSING_INDEX": IssueType.MISSING_INDEX,
                "FULL_SCAN": IssueType.FULL_SCAN,
                "REDUNDANT_INDEX": IssueType.MISSING_INDEX,
                "UNUSED_INDEX": IssueType.MISSING_INDEX,
                "WRONG_DATA_TYPE": IssueType.IMPLICIT_CAST,
                "MISSING_FK": IssueType.BAD_JOIN,
                "TABLE_BLOAT": IssueType.HIGH_COST,
                "OVER_INDEXED": IssueType.MISSING_INDEX,
                "MISSING_PK": IssueType.MISSING_INDEX,
                "LOW_CARDINALITY_INDEX": IssueType.MISSING_INDEX,
            }

            severity_map = {
                "CRITICAL": Severity.CRITICAL,
                "HIGH": Severity.HIGH,
                "MEDIUM": Severity.MEDIUM,
                "LOW": Severity.LOW,
            }

            issue_type = issue_type_map.get(issue_type_str, IssueType.MISSING_INDEX)
            severity = severity_map.get(severity_str, Severity.MEDIUM)

            issues.append(QueryIssue(
                issue_type=issue_type,
                severity=severity,
                description=f"{description}\nFix: {suggestion}",
                tables=[table_name]
            ))

        except Exception:
            continue

    return issues


def analyze_schema() -> List[QueryIssue]:
    """
    Main Schema Analyzer function.
    Analyzes all tables and returns list of QueryIssue objects.
    """
    all_issues = []

    print("=" * 60)
    print("SCHEMA ANALYZER AGENT")
    print("=" * 60)

    # Step 1: Get all tables
    print("\nGetting all tables...")
    tables = get_all_table_names.invoke({})
    print(f"Found {len(tables)} tables: {tables}")

    # Step 2: Get global schema info
    print("\nGetting schema details...")
    unused_indexes = get_unused_indexes.invoke({})
    tables_without_pks = get_tables_without_primary_keys.invoke({})
    missing_fk_indexes = get_missing_fk_indexes.invoke({})
    table_bloat = get_table_bloat.invoke({})

    # Step 3: Static detection
    print("\nRunning static detection...")

    # Tables without primary keys
    for table in tables_without_pks:
        all_issues.append(QueryIssue(
            issue_type=IssueType.MISSING_INDEX,
            severity=Severity.CRITICAL,
            description=f"Table '{table}' has no PRIMARY KEY! Data integrity risk.",
            tables=[table]
        ))
        print(f"  CRITICAL: {table} has no PRIMARY KEY!")

    # Unused indexes
    for idx in unused_indexes:
        all_issues.append(QueryIssue(
            issue_type=IssueType.MISSING_INDEX,
            severity=Severity.LOW,
            description=f"Index '{idx['indexname']}' on table '{idx['tablename']}' has never been used! Wastes write overhead.\nFix: DROP INDEX {idx['indexname']};",
            tables=[idx["tablename"]]
        ))
        print(f"  LOW: Unused index {idx['indexname']} on {idx['tablename']}")

    # Missing FK indexes
    for fk in missing_fk_indexes:
        all_issues.append(QueryIssue(
            issue_type=IssueType.MISSING_INDEX,
            severity=Severity.HIGH,
            description=f"FK column '{fk['fk_column']}' on table '{fk['table_name']}' has no index! Causes slow JOINs.\nFix: CREATE INDEX idx_{fk['table_name']}_{fk['fk_column']} ON {fk['table_name']}({fk['fk_column']});",
            tables=[fk["table_name"]]
        ))
        print(f"  HIGH: Missing FK index on {fk['table_name']}.{fk['fk_column']}")

    # Table bloat
    for bloat in table_bloat:
        if bloat["dead_ratio_percent"] > 10:
            all_issues.append(QueryIssue(
                issue_type=IssueType.HIGH_COST,
                severity=Severity.MEDIUM,
                description=f"Table '{bloat['table_name']}' has {bloat['dead_ratio_percent']}% dead tuples ({bloat['dead_rows']} dead rows)! Wastes storage.\nFix: VACUUM ANALYZE {bloat['table_name']};",
                tables=[bloat["table_name"]]
            ))
            print(f"  MEDIUM: Table bloat on {bloat['table_name']} ({bloat['dead_ratio_percent']}%)")

    # Step 4: LLM analysis per table
    print("\nRunning LLM analysis per table...")
    for table in tables:
        print(f"\n  Analyzing table: {table}")

        table_details = get_table_details.invoke(table)

        chain = schema_prompt | llm | parser
        llm_output = chain.invoke({
            "table_details": json.dumps(table_details, indent=2, default=str),
            "unused_indexes": json.dumps(unused_indexes, indent=2, default=str),
            "tables_without_pks": json.dumps(tables_without_pks, indent=2, default=str),
            "missing_fk_indexes": json.dumps(missing_fk_indexes, indent=2, default=str),
            "table_bloat": json.dumps(table_bloat, indent=2, default=str)
        })

        table_issues = parse_llm_issues(llm_output, table)
        all_issues.extend(table_issues)

        for issue in table_issues:
            severity_label = {
                Severity.CRITICAL: "CRITICAL",
                Severity.HIGH: "HIGH",
                Severity.MEDIUM: "MEDIUM",
                Severity.LOW: "LOW"
            }
            label = severity_label.get(issue.severity, "INFO")
            print(f"  [{label}] {issue.issue_type} - {issue.description}")

    return all_issues


def schema_analyzer_node(state: dict) -> dict:
    """LangGraph node for Schema Analyzer"""
    issues = analyze_schema()
    state["schema_issues"] = issues
    return state


def _print_issues(issues: List[QueryIssue]):
    """Pretty print QueryIssue list"""
    severity_label = {
        Severity.CRITICAL: "[CRITICAL]",
        Severity.HIGH:     "[HIGH]",
        Severity.MEDIUM:   "[MEDIUM]",
        Severity.LOW:      "[LOW]"
    }
    for issue in issues:
        label = severity_label.get(issue.severity, "[INFO]")
        print(f"\n  {label} {issue.issue_type}")
        print(f"     Table    : {', '.join(issue.tables)}")
        print(f"     Problem  : {issue.description}")
        


if __name__ == "__main__":
    issues = analyze_schema()

    print("\n" + "=" * 60)
    print("SCHEMA ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nTotal issues found: {len(issues)}")

    critical = [i for i in issues if i.severity == Severity.CRITICAL]
    high = [i for i in issues if i.severity == Severity.HIGH]
    medium = [i for i in issues if i.severity == Severity.MEDIUM]
    low = [i for i in issues if i.severity == Severity.LOW]

    print(f"Critical : {len(critical)}")
    print(f"High     : {len(high)}")
    print(f"Medium   : {len(medium)}")
    print(f"Low      : {len(low)}")

    print("\n" + "=" * 60)
    _print_issues(issues)