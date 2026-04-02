from typing import TypedDict, Dict, Any, List
from src.models.query_analysis import QueryIssue


class GraphState(TypedDict):
    query: str
    gorm_file: str  # optional: path to Go file with GORM queries
    parsed_sql: Dict[str, Any]
    execution_plan: Dict[str, Any]
    metrics: Dict[str, Any]
    issues: List[QueryIssue]