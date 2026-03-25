"""Query analysis model scaffold."""
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class IssueType(str, Enum):
    FULL_SCAN = "FULL_SCAN"
    MISSING_INDEX = "MISSING_INDEX"
    N_PLUS_ONE = "N_PLUS_ONE"
    CARTESIAN_JOIN = "CARTESIAN_JOIN"
    SELECT_STAR = "SELECT_STAR"

class QueryInput(BaseModel):
    query: str
    source_file: Optional[str] = None
    metadata: Optional[dict] = None

class ExecutionNode(BaseModel):
    node_type: str
    cost: float
    rows: int
    width: int
    actual_time: Optional[float] = None
    loops: Optional[int] = None

class ExecutionPlan(BaseModel):
    total_cost: float
    total_time: float
    nodes: List[ExecutionNode]

class QueryIssue(BaseModel):
    issue_type: IssueType
    severity: str
    description: str
    tables: List[str] = []
    columns: List[str] = []

class OptimizationSuggestion(BaseModel):
    original_query: str
    optimized_query: Optional[str]
    explanation: str
    expected_improvement: str

class AnalysisReport(BaseModel):
    issues: List[QueryIssue]
    suggestions: List[OptimizationSuggestion]
    performance_score: float