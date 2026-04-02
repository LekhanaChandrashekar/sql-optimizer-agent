from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class SchemaIssueType(str, Enum):
    WRONG_DATA_TYPE = "WRONG_DATA_TYPE"
    MISSING_INDEX = "MISSING_INDEX"
    DUPLICATE_INDEX = "DUPLICATE_INDEX"
    MISSING_FOREIGN_KEY = "MISSING_FOREIGN_KEY"
    MISSING_CONSTRAINT = "MISSING_CONSTRAINT"
    OVERLY_WIDE_COLUMN = "OVERLY_WIDE_COLUMN"
    MISSING_GIN_INDEX = "MISSING_GIN_INDEX"
    LOW_CARDINALITY_INDEX = "LOW_CARDINALITY_INDEX"
    WRONG_INDEX_ORDER = "WRONG_INDEX_ORDER"


class SchemaSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SchemaIssue(BaseModel):
    table: str
    column: Optional[str] = None
    issue_type: SchemaIssueType
    severity: SchemaSeverity
    description: str
    recommendation: str


class IndexRecommendation(BaseModel):
    table: str
    columns: List[str]
    index_type: str = "btree"
    reason: str
    estimated_improvement: str = ""
    create_statement: str = ""


class BottleneckResult(BaseModel):
    query: str
    bottleneck_type: str
    description: str
    severity: SchemaSeverity
    affected_nodes: List[str] = Field(default_factory=list)
    recommendation: str = ""


class OptimizationResult(BaseModel):
    original_query: str
    optimized_query: Optional[str] = None
    explanation: str
    index_recommendations: List[IndexRecommendation] = Field(default_factory=list)
    schema_changes: List[SchemaIssue] = Field(default_factory=list)
    expected_improvement: str = ""
    confidence: float = 0.0
