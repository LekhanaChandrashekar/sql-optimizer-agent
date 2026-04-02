import pytest
from src.tools.sql_parser import extract_metadata, detect_anti_patterns


def test_extract_tables_single():
    result = extract_metadata("SELECT * FROM users")
    assert result["tables"] == ["users"]


def test_extract_multiple_tables():
    query = "SELECT * FROM users u JOIN orders o ON u.id = o.user_id"
    result = extract_metadata(query)
    assert set(result["tables"]) == {"users", "orders"}


def test_detect_select_star():
    issues = detect_anti_patterns("SELECT * FROM users")
    assert "SELECT_STAR" in issues


def test_detect_cartesian_join_comma():
    issues = detect_anti_patterns("SELECT * FROM users u, orders o")
    assert "CARTESIAN_JOIN" in issues


def test_detect_cartesian_join_missing_on():
    issues = detect_anti_patterns("SELECT * FROM users JOIN orders")
    assert "CARTESIAN_JOIN" in issues


def test_where_clause_present():
    result = extract_metadata("SELECT * FROM users WHERE age > 30")
    assert result["has_where"] is True


def test_where_clause_absent():
    result = extract_metadata("SELECT * FROM users")
    assert result["has_where"] is False


def test_empty_query():
    result = extract_metadata("")
    assert result["tables"] == []
    assert result["columns"] == []


def test_subquery_detection():
    query = "SELECT * FROM (SELECT * FROM users) sub"
    result = extract_metadata(query)
    assert result["subqueries"] >= 1


def test_aggregation_detection():
    query = "SELECT COUNT(*) FROM users"
    result = extract_metadata(query)
    assert "COUNT" in result["aggregations"]