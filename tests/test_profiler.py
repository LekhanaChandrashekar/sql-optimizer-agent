import pytest
from src.agents.profiler import profiler_agent

BAD_QUERIES = [
    "SELECT * FROM users",
    "SELECT * FROM users WHERE email = 'x'",
    "SELECT * FROM users u JOIN orders o ON u.id = o.user_id",
    "SELECT * FROM users WHERE name LIKE '%abc%'",
    "SELECT * FROM users WHERE UPPER(name) = 'ABC'",
    "SELECT * FROM users u, orders o",
]


def test_profiler_outputs_issues():
    for query in BAD_QUERIES:
        result = profiler_agent({"query": query})

        assert "issues" in result
        assert len(result["issues"]) > 0