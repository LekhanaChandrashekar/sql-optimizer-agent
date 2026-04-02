import re
import sqlglot
from sqlglot import parse_one, exp


def extract_metadata(query: str):
    if not query or not query.strip():
        return {
            "tables": [],
            "columns": [],
            "joins": [],
            "subqueries": 0,
            "aggregations": [],
            "has_where": False,
        }

    try:
        tree = parse_one(query)
    except Exception:
        return {
            "tables": [],
            "columns": [],
            "joins": [],
            "subqueries": 0,
            "aggregations": [],
            "has_where": False,
        }

    tables = [t.name for t in tree.find_all(exp.Table) if t.name]
    columns = [c.name for c in tree.find_all(exp.Column) if c.name]
    joins = [j.kind for j in tree.find_all(exp.Join)]
    subqueries = len(list(tree.find_all(exp.Subquery)))
    aggregations = [a.key.upper() for a in tree.find_all(exp.AggFunc)]

    return {
        "tables": list(dict.fromkeys(tables)),
        "columns": list(dict.fromkeys(columns)),
        "joins": joins,
        "subqueries": subqueries,
        "aggregations": aggregations,
        "has_where": tree.find(exp.Where) is not None,
    }


def _extract_from_clause(query_upper: str) -> str:
    """Extract the FROM clause text (between FROM and WHERE/JOIN/ORDER/GROUP/HAVING/LIMIT/;/end)."""
    match = re.search(
        r'\bFROM\b(.*?)(?:\bWHERE\b|\bJOIN\b|\bORDER\b|\bGROUP\b|\bHAVING\b|\bLIMIT\b|;|$)',
        query_upper,
        re.DOTALL
    )
    return match.group(1).strip() if match else ""


def detect_anti_patterns(query: str):
    issues = set()
    q = query.upper()

    # SELECT *
    if "SELECT *" in q:
        issues.add("SELECT_STAR")

    # Cartesian join via comma in FROM clause only
    from_clause = _extract_from_clause(q)
    if "," in from_clause:
        issues.add("CARTESIAN_JOIN")

    # JOIN without ON/USING
    if "JOIN" in q and " ON " not in q and " USING " not in q:
        issues.add("CARTESIAN_JOIN")

    # Implicit cast
    if "::" in query:
        issues.add("IMPLICIT_CAST")

    # Leading wildcard
    if "LIKE '%" in q or "ILIKE '%" in q:
        issues.add("LEADING_WILDCARD")

    # Function on indexed column in WHERE
    if re.search(r'\bWHERE\b.*\b(UPPER|LOWER|TRIM|COALESCE)\s*\(', q):
        issues.add("FUNCTION_ON_INDEX")

    # NOT IN subquery (should be NOT EXISTS)
    if re.search(r'\bNOT\s+IN\s*\(\s*SELECT\b', q):
        issues.add("CORRELATED_SUBQUERY")

    # DISTINCT (potential unnecessary)
    if re.search(r'\bSELECT\s+DISTINCT\b', q):
        issues.add("UNNECESSARY_DISTINCT")

    return list(issues)