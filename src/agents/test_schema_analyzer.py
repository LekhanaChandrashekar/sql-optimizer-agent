import pytest
from unittest.mock import patch, MagicMock
from src.agents.schema_analyzer import analyze_schema, parse_llm_issues
from src.models.query_analysis import QueryIssue, IssueType, Severity


# Test 1: orders table must flag missing FK index
def test_missing_fk_index_detected():
    """orders.user_id has no index - must be flagged HIGH"""
    with patch("src.agents.schema_analyzer.get_all_table_names") as mock_tables, \
         patch("src.agents.schema_analyzer.get_unused_indexes") as mock_unused, \
         patch("src.agents.schema_analyzer.get_tables_without_primary_keys") as mock_pks, \
         patch("src.agents.schema_analyzer.get_missing_fk_indexes") as mock_fk, \
         patch("src.agents.schema_analyzer.get_table_bloat") as mock_bloat, \
         patch("src.agents.schema_analyzer.get_table_details") as mock_details, \
         patch("src.agents.schema_analyzer.llm") as mock_llm, \
         patch("src.agents.schema_analyzer.schema_prompt") as mock_prompt, \
         patch("src.agents.schema_analyzer.parser") as mock_parser:

        mock_tables.invoke.return_value = ["orders"]
        mock_unused.invoke.return_value = []
        mock_pks.invoke.return_value = []
        mock_fk.invoke.return_value = [
            {
                "table_name": "orders",
                "fk_column": "user_id",
                "references_table": "users"
            }
        ]
        mock_bloat.invoke.return_value = []
        mock_details.invoke.return_value = {"table_name": "orders", "columns": []}

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ""
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        issues = analyze_schema()

        fk_issues = [
            i for i in issues
            if "user_id" in i.description and i.severity == Severity.HIGH
        ]
        assert len(fk_issues) > 0, "Missing FK index on orders.user_id not detected!"


# Test 2: table without primary key must flag CRITICAL
def test_missing_primary_key_detected():
    """Table without PK must be flagged CRITICAL"""
    with patch("src.agents.schema_analyzer.get_all_table_names") as mock_tables, \
         patch("src.agents.schema_analyzer.get_unused_indexes") as mock_unused, \
         patch("src.agents.schema_analyzer.get_tables_without_primary_keys") as mock_pks, \
         patch("src.agents.schema_analyzer.get_missing_fk_indexes") as mock_fk, \
         patch("src.agents.schema_analyzer.get_table_bloat") as mock_bloat, \
         patch("src.agents.schema_analyzer.get_table_details") as mock_details, \
         patch("src.agents.schema_analyzer.llm") as mock_llm, \
         patch("src.agents.schema_analyzer.schema_prompt") as mock_prompt, \
         patch("src.agents.schema_analyzer.parser") as mock_parser:

        mock_tables.invoke.return_value = ["bad_table"]
        mock_unused.invoke.return_value = []
        mock_pks.invoke.return_value = ["bad_table"]
        mock_fk.invoke.return_value = []
        mock_bloat.invoke.return_value = []
        mock_details.invoke.return_value = {"table_name": "bad_table", "columns": []}

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ""
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        issues = analyze_schema()

        critical_issues = [
            i for i in issues
            if i.severity == Severity.CRITICAL
        ]
        assert len(critical_issues) > 0, "Missing PK not flagged as CRITICAL!"


# Test 3: unused index must be flagged LOW
def test_unused_index_detected():
    """Unused index must be flagged LOW"""
    with patch("src.agents.schema_analyzer.get_all_table_names") as mock_tables, \
         patch("src.agents.schema_analyzer.get_unused_indexes") as mock_unused, \
         patch("src.agents.schema_analyzer.get_tables_without_primary_keys") as mock_pks, \
         patch("src.agents.schema_analyzer.get_missing_fk_indexes") as mock_fk, \
         patch("src.agents.schema_analyzer.get_table_bloat") as mock_bloat, \
         patch("src.agents.schema_analyzer.get_table_details") as mock_details, \
         patch("src.agents.schema_analyzer.llm") as mock_llm, \
         patch("src.agents.schema_analyzer.schema_prompt") as mock_prompt, \
         patch("src.agents.schema_analyzer.parser") as mock_parser:

        mock_tables.invoke.return_value = ["orders"]
        mock_unused.invoke.return_value = [
            {
                "indexname": "idx_orders_status",
                "tablename": "orders",
                "times_used": 0,
                "index_size": "8192 bytes"
            }
        ]
        mock_pks.invoke.return_value = []
        mock_fk.invoke.return_value = []
        mock_bloat.invoke.return_value = []
        mock_details.invoke.return_value = {"table_name": "orders", "columns": []}

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ""
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        issues = analyze_schema()

        low_issues = [
            i for i in issues
            if i.severity == Severity.LOW
        ]
        assert len(low_issues) > 0, "Unused index not detected!"


# Test 4: table bloat must be flagged MEDIUM
def test_table_bloat_detected():
    """Table with >10% dead tuples must be flagged MEDIUM"""
    with patch("src.agents.schema_analyzer.get_all_table_names") as mock_tables, \
         patch("src.agents.schema_analyzer.get_unused_indexes") as mock_unused, \
         patch("src.agents.schema_analyzer.get_tables_without_primary_keys") as mock_pks, \
         patch("src.agents.schema_analyzer.get_missing_fk_indexes") as mock_fk, \
         patch("src.agents.schema_analyzer.get_table_bloat") as mock_bloat, \
         patch("src.agents.schema_analyzer.get_table_details") as mock_details, \
         patch("src.agents.schema_analyzer.llm") as mock_llm, \
         patch("src.agents.schema_analyzer.schema_prompt") as mock_prompt, \
         patch("src.agents.schema_analyzer.parser") as mock_parser:

        mock_tables.invoke.return_value = ["orders"]
        mock_unused.invoke.return_value = []
        mock_pks.invoke.return_value = []
        mock_fk.invoke.return_value = []
        mock_bloat.invoke.return_value = [
            {
                "table_name": "orders",
                "live_rows": 1000,
                "dead_rows": 200,
                "dead_ratio_percent": 20.0
            }
        ]
        mock_details.invoke.return_value = {"table_name": "orders", "columns": []}

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ""
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        issues = analyze_schema()

        bloat_issues = [
            i for i in issues
            if "dead" in i.description.lower() or "bloat" in i.description.lower()
        ]
        assert len(bloat_issues) > 0, "Table bloat not detected!"


# Test 5: LLM output correctly parsed
def test_llm_output_parsed_correctly():
    """LLM output must be correctly parsed into QueryIssue objects"""
    llm_output = """
ISSUE_TYPE: WRONG_DATA_TYPE
SEVERITY: HIGH
TABLE: orders
DESCRIPTION: total_amount is TEXT but should be DECIMAL
SUGGESTION: ALTER TABLE orders ALTER COLUMN total_amount TYPE DECIMAL;
---
ISSUE_TYPE: MISSING_INDEX
SEVERITY: MEDIUM
TABLE: products
DESCRIPTION: No index on category column
SUGGESTION: CREATE INDEX idx_products_category ON products(category);
---
"""
    issues = parse_llm_issues(llm_output, "orders")

    assert len(issues) == 2, f"Expected 2 issues, got {len(issues)}"
    assert issues[0].severity == Severity.HIGH
    assert issues[1].severity == Severity.MEDIUM


# Test 6: good table produces no static issues
def test_good_table_no_static_issues():
    """Well designed table should produce no static issues"""
    with patch("src.agents.schema_analyzer.get_all_table_names") as mock_tables, \
         patch("src.agents.schema_analyzer.get_unused_indexes") as mock_unused, \
         patch("src.agents.schema_analyzer.get_tables_without_primary_keys") as mock_pks, \
         patch("src.agents.schema_analyzer.get_missing_fk_indexes") as mock_fk, \
         patch("src.agents.schema_analyzer.get_table_bloat") as mock_bloat, \
         patch("src.agents.schema_analyzer.get_table_details") as mock_details, \
         patch("src.agents.schema_analyzer.llm") as mock_llm, \
         patch("src.agents.schema_analyzer.schema_prompt") as mock_prompt, \
         patch("src.agents.schema_analyzer.parser") as mock_parser:

        mock_tables.invoke.return_value = ["users"]
        mock_unused.invoke.return_value = []
        mock_pks.invoke.return_value = []
        mock_fk.invoke.return_value = []
        mock_bloat.invoke.return_value = []
        mock_details.invoke.return_value = {"table_name": "users", "columns": []}

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ""
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_llm.__or__ = MagicMock(return_value=mock_chain)

        issues = analyze_schema()

        assert len(issues) == 0, f"Good table should have no issues, got {len(issues)}"


if __name__ == "__main__":
    print("Running Schema Analyzer Tests...")
    print("=" * 50)
    test_missing_fk_index_detected()
    test_missing_primary_key_detected()
    test_unused_index_detected()
    test_table_bloat_detected()
    test_llm_output_parsed_correctly()
    test_good_table_no_static_issues()
    print("=" * 50)
    print("All 6 tests passed!")