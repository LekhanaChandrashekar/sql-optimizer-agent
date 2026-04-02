import pytest
from unittest.mock import patch
from src.tools.db_connector import run_explain, validate_query

# UNIT TESTS (NO DB)

def test_validate_query_success():
    validate_query("SELECT * FROM users")


def test_forbidden_query():
    with pytest.raises(ValueError):
        validate_query("DROP TABLE users")


def test_empty_query():
    with pytest.raises(ValueError):
        validate_query("")

# MOCKED DB TEST

@patch("src.tools.db_connector.get_connection")
def test_run_explain_mock(mock_conn):
    mock_cursor = mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value

    mock_cursor.fetchone.return_value = [
        [{"Plan": {"Node Type": "Seq Scan"}, "Execution Time": 1.2}]
    ]

    result = run_explain("SELECT 1")

    assert result["Plan"]["Node Type"] == "Seq Scan"

# INTEGRATION TESTS (REAL DB)


@pytest.mark.integration
def test_explain_structure():
    result = run_explain("SELECT 1")
    assert "Plan" in result


@pytest.mark.integration
def test_limit_query():
    result = run_explain("SELECT * FROM users LIMIT 1")
    assert result is not None