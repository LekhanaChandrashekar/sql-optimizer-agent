from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class IssueType(str, Enum):
    FULL_SCAN = "FULL_SCAN"
    MISSING_INDEX = "MISSING_INDEX"
    N_PLUS_ONE = "N_PLUS_ONE"
    CARTESIAN_JOIN = "CARTESIAN_JOIN"
    SELECT_STAR = "SELECT_STAR"
    IMPLICIT_CAST = "IMPLICIT_CAST"
    BAD_JOIN = "BAD_JOIN"
    LEADING_WILDCARD = "LEADING_WILDCARD"
    FUNCTION_ON_INDEX = "FUNCTION_ON_INDEX"
    OVER_FETCHING = "OVER_FETCHING"
    MISSING_PAGINATION = "MISSING_PAGINATION"
    UNNECESSARY_DISTINCT = "UNNECESSARY_DISTINCT"
    UNINDEXED_SORT = "UNINDEXED_SORT"
    HIGH_COST = "HIGH_COST"
    CORRELATED_SUBQUERY = "CORRELATED_SUBQUERY"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QueryInput(BaseModel):
    query: str
    source_file: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionNode(BaseModel):
    node_type: str
    total_cost: float
    plan_rows: int
    plan_width: int
    actual_time: Optional[float] = 0.0
    loops: Optional[int] = 0
    relation_name: Optional[str] = None


class ExecutionPlan(BaseModel):
    total_cost: float
    execution_time: float
    nodes: List[ExecutionNode]


class QueryIssue(BaseModel):
    issue_type: IssueType
    severity: Severity
    description: str
    tables: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)


class OptimizationSuggestion(BaseModel):
    original_query: str
    optimized_query: Optional[str] = None
    explanation: str
    expected_improvement: str
    confidence: float = 0.0


class AnalysisReport(BaseModel):
    query: str
    issues: List[QueryIssue]
    suggestions: List[OptimizationSuggestion]
    performance_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)