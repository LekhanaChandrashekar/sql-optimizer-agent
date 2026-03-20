# Plan: AI SQL Query Optimization Agent — 8-Week Intern Project

## TL;DR
Build a LangGraph-based multi-agent system (Python) + Go GORM parser that analyzes PostgreSQL queries for performance issues, detects bottlenecks, and generates optimized alternatives with explanations. Uses Claude Opus 4.6 as the LLM. Two interns, 8 weeks. CLI-first with FastAPI service and CI integration added later.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   CLI / FastAPI                  │
│              (User Interface Layer)              │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│            LangGraph Orchestrator               │
│         (State Graph + Routing Logic)           │
├─────────┬──────────┬──────────┬─────────────────┤
│ Profiler│Bottleneck│Optimizer │ Schema Analyzer  │
│  Agent  │ Detector │  Agent   │     Agent        │
│         │  Agent   │          │                  │
└────┬────┴────┬─────┴────┬────┴────┬─────────────┘
     │         │          │         │
┌────▼─────────▼──────────▼─────────▼─────────────┐
│              LangChain Tools                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ SQL      │ │ DB       │ │ Go GORM Parser   │ │
│  │ Parser   │ │ Connector│ │ (subprocess)     │ │
│  │(sqlglot) │ │(psycopg2)│ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Components:**
- **Orchestrator**: LangGraph state graph that routes queries through agents based on analysis type
- **Profiler Agent**: Runs EXPLAIN ANALYZE, extracts execution metrics, identifies slow operations
- **Bottleneck Detector Agent**: Analyzes query patterns for scalability risks (N+1, locking, full scans)
- **Optimizer Agent**: Generates optimized queries with rationale using Claude
- **Schema Analyzer Agent**: Reviews table design, indexes, data types, normalization
- **Go GORM Parser**: Standalone Go binary that parses `.go` files, extracts GORM method chains, converts to approximate SQL

## Intern Work Split

- **Intern A (Python/AI focus)**: LangGraph orchestrator, Profiler Agent, Optimizer Agent, CLI, FastAPI, reporting
- **Intern B (Go/Database focus)**: Go GORM Parser, Bottleneck Detector Agent, Schema Analyzer Agent, test database, CI integration

Both collaborate on integration, testing, and documentation.

---

## Week-by-Week Plan

### Phase 1: Foundation & Learning (Weeks 1–2)

#### Week 1: Environment Setup & Core Concepts

**Both Interns:**
- [ ] Set up development environment: Python 3.11+, Go 1.22+, PostgreSQL 16, Docker
- [ ] Install and configure: `uv` (Python package manager), `langchain`, `langgraph`, `sqlglot`, `psycopg2`
- [ ] Complete LangChain tutorial: https://python.langchain.com/docs/tutorials/ (focus on "Build a Chatbot" and "Build an Agent")
- [ ] Complete LangGraph tutorial: https://langchain-ai.github.io/langgraph/tutorials/introduction/ (focus on "Quick Start" and "Chatbot" tutorials)
- [ ] Read PostgreSQL EXPLAIN documentation: https://www.postgresql.org/docs/current/sql-explain.html
- [ ] Study infoblox repo's GORM patterns (review `pkg/svc/lab_features.go`, `pkg/svc/watchlist_features.go`)
- [ ] Set up the project repo with this structure:
  ```
  sql-optimizer-agent/
  ├── pyproject.toml              # Python deps (langchain, langgraph, sqlglot, etc.)
  ├── src/
  │   ├── cli/                    # CLI entry point (Typer)
  │   ├── orchestrator/           # LangGraph state graph
  │   ├── agents/                 # Individual agent implementations
  │   │   ├── profiler.py
  │   │   ├── bottleneck.py
  │   │   ├── optimizer.py
  │   │   └── schema_analyzer.py
  │   ├── tools/                  # LangChain tools
  │   │   ├── sql_parser.py       # sqlglot-based parsing
  │   │   ├── db_connector.py     # PostgreSQL connection + EXPLAIN runner
  │   │   └── gorm_parser.py      # Wrapper to invoke Go GORM parser binary
  │   └── models/                 # Pydantic data models
  │       ├── query_analysis.py
  │       └── optimization.py
  ├── gorm-parser/                # Go module for GORM source code parsing
  │   ├── go.mod
  │   ├── main.go
  │   ├── parser/
  │   │   ├── ast_walker.go       # Go AST traversal
  │   │   ├── gorm_extractor.go   # GORM method chain extraction
  │   │   └── sql_emitter.go      # Convert GORM chains to SQL
  │   └── testdata/               # Sample Go files for testing
  ├── test-db/                    # Test database setup
  │   ├── docker-compose.yml
  │   ├── schema.sql              # Intentionally flawed schema for testing
  │   ├── seed_data.sql           # Sample data
  │   └── bad_queries.sql         # Intentionally inefficient queries
  ├── tests/                      # Python tests
  └── docs/
  ```
- [ ] Create initial `pyproject.toml` with dependencies:
    - `langchain-anthropic` (Claude Opus 4.6)
    - `langgraph`
    - `sqlglot`
    - `psycopg2-binary`
    - `typer` (CLI framework)
    - `rich` (terminal output formatting)
    - `pydantic` (data models)
    - `pytest`, `pytest-asyncio` (testing)

**End-of-Week Deliverable:** Repo scaffolded, environments working, both interns can run a basic LangChain "hello world" with Claude Opus 4.6. Both interns have read and understood the infoblox GORM code patterns.

---

#### Week 2: Core Tools & Data Models

**Intern A (Python/AI):**
- [ ] Define Pydantic data models for the pipeline:
    - `QueryInput`: raw SQL string, source file (optional), context metadata
    - `ExecutionPlan`: parsed EXPLAIN output (node type, cost, rows, width, actual time, loops)
    - `QueryIssue`: issue type enum (FULL_SCAN, MISSING_INDEX, N_PLUS_ONE, etc.), severity, description, affected tables/columns
    - `OptimizationSuggestion`: original query, optimized query, explanation, expected improvement
    - `AnalysisReport`: aggregation of all findings with performance score
- [ ] Build the `db_connector` tool:
    - Connect to PostgreSQL using `psycopg2`
    - Run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on input queries
    - Parse the JSON output into `ExecutionPlan` model
    - Extract key metrics: total cost, sequential scans, index scans, sort operations, hash joins
    - Handle query timeout (set `statement_timeout` for safety)
    - **Security**: Use read-only connection role, parameterized queries only, no DDL/DML allowed
- [ ] Build the `sql_parser` tool using `sqlglot`:
    - Parse SQL into AST
    - Extract: tables referenced, join types, WHERE conditions, subqueries, aggregations
    - Detect common anti-patterns statically: `SELECT *`, cartesian joins, implicit type casts, functions on indexed columns
    - Output structured metadata for agents to consume
- [ ] Write unit tests for both tools (minimum 5 tests each covering happy path, error cases, edge cases)

**Intern B (Go/Database):**
- [ ] Build the Go GORM parser — Phase 1 (AST walker):
    - Use `go/parser` and `go/ast` to parse Go source files
    - Walk the AST to find call expressions on `*gorm.DB` type
    - Identify GORM method chains: `.Where()`, `.First()`, `.Find()`, `.Create()`, `.Save()`, `.Updates()`, `.Delete()`
    - Extract string literals from `.Where()` arguments as SQL fragments
    - Output JSON: `{"chains": [{"methods": ["Where", "First"], "sql_fragments": ["id = ?"], "file": "lab_features.go", "line": 118}]}`
    - Test against feature.lab's actual Go files in `testdata/`
- [ ] Set up the test database:
    - Create `docker-compose.yml` that starts PostgreSQL 16
    - Write `schema.sql` with intentionally flawed schema:
        - Table with no indexes (simulate full scan issues)
        - Table with redundant indexes
        - Unnormalized table with duplicate data
        - Table missing foreign keys
        - Table with overly wide VARCHAR types
        - JSONB column without GIN index
    - Include feature.lab's actual schema (from migrations) as a "good" baseline
    - Write `seed_data.sql`: generate 100K+ rows using `generate_series` for meaningful EXPLAIN results
    - Write `bad_queries.sql`: 15+ intentionally inefficient queries:
        - `SELECT *` on large tables
        - Missing WHERE clause on large table
        - JOIN without index on join key
        - `NOT IN` subquery (should be `NOT EXISTS`)
        - `LIKE '%pattern%'` (leading wildcard)
        - `ORDER BY` on non-indexed column with `LIMIT`
        - Function on indexed column in WHERE (`WHERE UPPER(name) = 'FOO'`)
        - Cartesian join
        - Correlated subquery
        - N+1 pattern (sequential single-row fetches)
        - Unneded DISTINCT
        - Over-fetching columns
        - Missing pagination
        - Inefficient `COUNT(*)` with complex WHERE
        - JSONB query without GIN index
- [ ] Write Go unit tests for the AST walker (minimum 8 tests covering each GORM method pattern from feature.lab)

**End-of-Week Deliverable:** `db_connector` tool can run EXPLAIN on PostgreSQL and return structured metrics. `sql_parser` tool can parse SQL and detect basic anti-patterns. Go GORM parser can extract method chains from Go files. Test database is up with seeded data.

---

### Phase 2: Agent Implementation (Weeks 3–4)

#### Week 3: Profiler Agent & Bottleneck Detector

**Intern A — Profiler Agent:**
- [ ] Implement the Profiler Agent as a LangGraph node:
    - Input: `QueryInput` (raw SQL or SQL from GORM parser)
    - Tools available: `db_connector` (EXPLAIN runner), `sql_parser`
    - Agent behavior:
        1. Parse SQL with `sql_parser` to get structural metadata
        2. Run EXPLAIN ANALYZE via `db_connector`
        3. Use Claude to interpret the execution plan and identify:
            - Sequential scans on tables > 1000 rows
            - High-cost operations (cost > threshold)
            - Nested loops with large row estimates
            - Sort operations not backed by indexes
            - Hash joins that could be merge joins
        4. Output: list of `QueryIssue` objects with severity (critical/warning/info)
    - Prompt engineering: Write a detailed system prompt for Claude that includes:
        - PostgreSQL execution plan node types and what they mean
        - Heuristics for "good" vs "bad" execution metrics
        - Examples of issue detection with expected output format
- [ ] Write tests: Feed the 15 bad queries from `bad_queries.sql` through the profiler, assert each produces at least one relevant issue
- [ ] Implement caching: Cache EXPLAIN results by query hash to avoid redundant DB calls

**Intern B — Bottleneck Detector Agent:**
- [ ] Implement the Bottleneck Detector Agent as a LangGraph node:
    - Input: `QueryInput` + `ExecutionPlan` (from Profiler)
    - Agent behavior — detect patterns that degrade under load:
        1. **Lock contention risk**: Queries that touch many rows with UPDATE/DELETE without proper WHERE clauses
        2. **N+1 detection**: Multiple similar queries in a batch (detect from GORM parser output — repeated `.Where("id = ?").First()` in loops)
        3. **Full scan on growing tables**: Sequential scans on tables with no row-count bound
        4. **Inefficient pagination**: `OFFSET`-based pagination on large datasets (suggest keyset pagination)
        5. **Sort without index**: `ORDER BY` on non-indexed columns with `LIMIT`
        6. **Missing partial indexes**: Queries that filter on status columns without partial indexes
    - Use Claude for nuanced analysis with a system prompt focused on scalability patterns
    - Output: list of `QueryIssue` objects tagged as "scalability" category
- [ ] Extend Go GORM parser — Phase 2:
    - Detect N+1 patterns: `.Where("id = ?").First()` inside `for` loops
    - Detect missing `.Preload()` for related data access patterns
    - Detect transaction scope issues (long-held transactions)
    - Output N+1 warnings in the JSON output
- [ ] Write integration tests: Run bottleneck detector on feature.lab's known patterns (bulk fetch + map pattern should pass, simulated N+1 should flag)

**End-of-Week Deliverable:** Profiler Agent analyzes queries and returns structured issues. Bottleneck Detector identifies scalability risks. GORM parser detects N+1 patterns.

---

#### Week 4: Optimizer Agent & Schema Analyzer

**Intern A — Optimizer Agent:**
- [ ] Implement the Optimizer Agent as a LangGraph node:
    - Input: `QueryInput` + list of `QueryIssue` from Profiler and Bottleneck Detector
    - Agent behavior:
        1. For each issue, generate an optimized version of the query
        2. Use Claude with a detailed prompt that includes:
            - The original query
            - The execution plan
            - The identified issues
            - The table schema (columns, indexes, constraints)
            - Instructions to generate: optimized SQL, CREATE INDEX statements if needed, explanation of each change
        3. Run EXPLAIN ANALYZE on the optimized query to verify improvement
        4. Calculate improvement metrics: cost reduction %, row estimate improvement, scan type changes
        5. If optimization makes things worse, discard and explain why
    - Output: list of `OptimizationSuggestion` objects with before/after metrics
- [ ] Handle optimization categories:
    - **Index suggestions**: Generate `CREATE INDEX` with rationale
    - **Query rewriting**: Transform `NOT IN` → `NOT EXISTS`, subquery → JOIN, etc.
    - **Column pruning**: Replace `SELECT *` with specific columns
    - **Pagination fix**: Replace `OFFSET/LIMIT` with keyset pagination
    - **JSONB optimization**: Suggest GIN indexes for `@>` queries
- [ ] Write tests: For each of the 15 bad queries, assert the optimizer produces an improvement (or correctly explains why it can't)

**Intern B — Schema Analyzer Agent:**
- [ ] Implement the Schema Analyzer Agent as a LangGraph node:
    - Input: Database connection (reads `information_schema` and `pg_catalog`)
    - Agent behavior:
        1. Query `information_schema.tables`, `information_schema.columns`, `pg_indexes`, `pg_stat_user_tables`, `pg_stat_user_indexes`
        2. Use Claude to analyze and detect:
            - Tables without primary keys
            - Missing foreign key constraints
            - Redundant indexes (indexes that are prefixes of other indexes)
            - Unused indexes (`pg_stat_user_indexes.idx_scan = 0`)
            - Columns with suboptimal types (e.g., `TEXT` where `VARCHAR(n)` or `ENUM` would be better)
            - Tables without any indexes
            - Missing indexes on foreign key columns
            - Over-indexed tables (index write overhead)
        3. Output: list of `QueryIssue` tagged as "schema" category
    - Build the `schema_reader` tool:
        - Fetch table definitions, column types, indexes, constraints, table statistics
        - Format as structured data for Claude to analyze
- [ ] Write tests against the test database: assert that the deliberately flawed tables produce correct warnings

**End-of-Week Deliverable:** Optimizer generates improved queries with before/after metrics. Schema Analyzer detects design issues. All four agents work independently.

---

### Phase 3: Integration & CLI (Weeks 5–6)

#### Week 5: LangGraph Orchestrator & CLI

**Intern A — LangGraph Orchestrator:**
- [ ] Implement the LangGraph state graph:
    - Define the state schema:
      ```python
      class AnalysisState(TypedDict):
          query_input: QueryInput
          execution_plan: Optional[ExecutionPlan]
          profiler_issues: list[QueryIssue]
          bottleneck_issues: list[QueryIssue]
          schema_issues: list[QueryIssue]
          optimizations: list[OptimizationSuggestion]
          report: Optional[AnalysisReport]
      ```
    - Define the graph flow:
        1. START → `parse_input` (determine if SQL or Go file)
        2. If Go file → `gorm_parser` node (invoke Go binary) → extracts SQL queries
        3. `profiler` node → runs EXPLAIN, identifies issues
        4. `bottleneck_detector` node (parallel with profiler for static checks)
        5. Conditional: if issues found → `optimizer` node
        6. Optional: `schema_analyzer` node (triggered by `--schema` flag)
        7. `report_generator` node → compile final `AnalysisReport`
        8. END
    - Implement conditional edges: skip optimizer if no issues found, skip schema if not requested
    - Add human-in-the-loop checkpoint before applying any index suggestions (for future use)
- [ ] Build the CLI using Typer:
    - `sql-agent analyze --query "SELECT * FROM ..."` — analyze a single query
    - `sql-agent analyze --file queries.sql` — analyze all queries in a file
    - `sql-agent analyze --go-file pkg/svc/lab_features.go` — parse GORM code and analyze extracted queries
    - `sql-agent schema --db-url postgresql://...` — run schema analysis
    - `sql-agent report --format json|markdown|terminal` — output format
    - Global options: `--db-url`, `--verbose`, `--timeout`
    - Use `rich` for colored terminal output with tables and progress bars
- [ ] Write integration tests: End-to-end test that feeds a bad query through the full pipeline and verifies the report contains expected issues and optimizations

**Intern B — Go GORM Parser Finalization & Integration:**
- [ ] Finalize Go GORM parser:
    - Handle all 28 GORM patterns cataloged from feature.lab
    - Add support for `gorm.Expr()`, `Omit()`, `Unscoped()`, `Set("gorm:query_option")`
    - Handle transaction boundaries (mark queries as "in transaction")
    - Generate parameterized SQL approximations (replace `?` placeholders with type-appropriate sample values for EXPLAIN)
    - Build as standalone binary: `gorm-parser analyze --file path/to/file.go --output json`
- [ ] Create Python wrapper tool (`tools/gorm_parser.py`):
    - Invoke Go binary as subprocess
    - Parse JSON output into `QueryInput` objects
    - Handle errors (binary not found, parse failures)
- [ ] Integration testing with feature.lab:
    - Run parser on `pkg/svc/lab_features.go` — verify it extracts the ~25 GORM query patterns correctly
    - Run parser on `pkg/svc/watchlist_features.go` — verify it extracts the ~17 patterns
    - Run extracted queries through the full pipeline
- [ ] Write E2E test: `gorm-parser analyze pkg/svc/lab_features.go | sql-agent analyze --stdin`

**End-of-Week Deliverable:** Full pipeline works end-to-end via CLI. Can analyze raw SQL, SQL files, and Go/GORM source files. Terminal output shows issues and optimizations in a formatted report.

---

#### Week 6: Reporting, FastAPI Service & Refinement

**Intern A — Reporting & FastAPI:**
- [ ] Build the report generator:
    - Terminal report: Rich-formatted tables showing issues by severity, optimizations with before/after costs, schema warnings
    - Markdown report: Exportable report suitable for PRs or documentation
    - JSON report: Machine-readable for CI integration
    - Performance score: 0-100 based on weighted issue counts (critical = -20, warning = -10, info = -5, starting from 100)
    - Include query fingerprinting: group similar queries together
- [ ] Build the FastAPI service:
    - `POST /analyze` — accepts `{"query": "...", "db_url": "..."}`, returns JSON report
    - `POST /analyze/file` — accepts SQL file upload
    - `POST /analyze/gorm` — accepts Go file upload, runs GORM parser + analysis
    - `POST /schema` — runs schema analysis on provided DB URL
    - `GET /health` — health check
    - Add request validation, error handling, timeouts
    - **Security**: Validate DB URLs (whitelist allowed hosts), sanitize file uploads, rate limiting
- [ ] Write API tests using `httpx` test client

**Intern B — CI Integration & Polish:**
- [ ] Build CI integration mode:
    - `sql-agent ci --migrations-dir db/migrations/ --db-url ...` — analyze new migration files
    - `sql-agent ci --changed-files file1.go file2.go` — analyze GORM changes in modified files
    - Exit code: 0 = pass, 1 = critical issues found, 2 = warnings only
    - Output: GitHub-compatible annotations format (file, line, message, severity)
- [ ] Create a GitHub Actions workflow template:
  ```yaml
  # .github/workflows/sql-analysis.yml
  # Triggered on PRs that modify .sql or pkg/svc/*.go files
  ```
- [ ] Performance optimization:
    - Add connection pooling for DB connector
    - Parallelize independent agent runs (profiler + static bottleneck checks)
    - Add query result caching (LRU by query hash)
- [ ] Write integration tests for CI mode against the test database

**End-of-Week Deliverable:** CLI produces formatted reports in 3 formats. FastAPI service handles requests. CI mode can be integrated into GitHub Actions.

---

### Phase 4: Testing, Documentation & Demo (Weeks 7–8)

#### Week 7: Comprehensive Testing & Edge Cases

**Both Interns:**
- [ ] Build comprehensive test suite:
    - **Unit tests** (minimum 90% coverage per component):
        - SQL parser: 15+ tests (various SQL dialects, edge cases, malformed SQL)
        - DB connector: 10+ tests (connection errors, timeouts, permission denied, empty results)
        - GORM parser: 15+ tests (all 28 patterns, malformed Go files, non-GORM code)
        - Each agent: 10+ tests (various issue types, no-issue queries, error handling)
        - Report generator: 5+ tests (each format, empty reports, large reports)
    - **Integration tests** (end-to-end pipeline):
        - Run all 15 bad queries through full pipeline — verify each gets correct issues + optimizations
        - Run feature.lab's actual queries — verify no false positives on known-good patterns (bulk fetch + map)
        - Run GORM parser on feature.lab source files — verify extraction accuracy
        - Test schema analyzer on both flawed and good schemas
    - **Edge case tests**:
        - Empty query input
        - Query with syntax errors
        - DB connection failure mid-analysis
        - Extremely long queries (> 10KB)
        - Queries with CTEs (WITH clauses)
        - Queries with window functions
        - Multi-statement SQL files
- [ ] Test against feature.lab's actual schema:
    - Load feature.lab migrations into test DB
    - Seed with realistic data volumes (100K activations, 50K interests, 10K features)
    - Run schema analyzer — verify it correctly identifies the existing good practices (partial indexes, GIN indexes, composite indexes)
    - Run profiler on the JSONB containment query pattern — verify it recognizes GIN index usage
    - Run bottleneck detector on the manual pagination pattern — verify it flags as potential issue

**Intern A additionally:**
- [ ] Add retry logic for transient Claude API failures
- [ ] Add token usage tracking and cost estimation per analysis
- [ ] Add `--dry-run` mode that shows what would be analyzed without running EXPLAIN

**Intern B additionally:**
- [ ] Add Docker packaging: `Dockerfile` that builds both Go parser binary and Python app
- [ ] Create `docker-compose.yml` for full local setup (app + test PostgreSQL)
- [ ] Add `Makefile` with targets: `build`, `test`, `lint`, `docker-build`, `docker-run`

**End-of-Week Deliverable:** Full test suite passing. Docker packaging done. Both agents tested against feature.lab real-world patterns.

---

#### Week 8: Documentation, Demo & Handoff

**Both Interns:**
- [ ] Write project documentation:
    - `README.md`: Project overview, quick start, installation, usage examples
    - `docs/architecture.md`: System architecture, data flow, agent responsibilities
    - `docs/adding-rules.md`: How to add new optimization rules / detection patterns
    - `docs/configuration.md`: Environment variables, CLI options, API endpoints
    - `docs/testing.md`: How to run tests, add test cases, test database setup
- [ ] Prepare demo:
    - Demo script with 5 scenarios:
        1. Analyze a single slow query → show issues + optimized version
        2. Analyze a Go/GORM file → show extracted queries + analysis
        3. Run schema analysis on test DB → show design issues
        4. Run CI mode on a "bad" migration file → show failure output
        5. FastAPI service demo → POST a query, get JSON report
    - Record a demo video (5-10 minutes)
- [ ] Create presentation slides covering:
    - Problem statement and motivation
    - Architecture and technical approach
    - Key results and metrics (number of issues detected across test suite)
    - Feature.lab case study (what the agent found)
    - Future roadmap

**Intern A additionally:**
- [ ] Write a "Getting Started" guide for developers adopting the tool
- [ ] Add `--explain` mode that outputs educational content about each optimization technique

**Intern B additionally:**
- [ ] Write contributor guide for extending database support (MySQL, SQLite)
- [ ] Create a template for adding new detection rules
- [ ] Tag v1.0.0 release

**End-of-Week Deliverable:** Documentation complete. Demo ready. Project handed off with contributor guides.

---

## Relevant Files (Feature.Lab Reference)

- `pkg/svc/lab_features.go` — 25+ GORM patterns, bulk fetch + map, transactions, JSONB queries
- `pkg/svc/watchlist_features.go` — 17 GORM patterns, collection operators, Omit, gorm.Expr
- `pkg/common/account_filter.go` — PostgreSQL JSONB containment query with GIN index
- `pkg/svc/expiry_monitor.go` — Date comparison queries with NULL checks
- `db/migrations/` — 27 migrations showing schema evolution, partial indexes, GIN indexes
- `config/dbConfig.go` — Database configuration pattern
- `db/db.go` — Connection pooling, migration runner

## Verification

1. **Unit test coverage**: Run `pytest --cov` — verify ≥90% coverage on each module
2. **Go parser accuracy**: Parse feature.lab's `lab_features.go` and `watchlist_features.go` — verify all 28+ GORM patterns extracted correctly
3. **Bad query detection**: Feed all 15 bad queries from `bad_queries.sql` — verify each gets at least one relevant issue flagged
4. **False positive rate**: Run feature.lab's known-good patterns (bulk fetch + map, partial indexes) — verify no false critical/warning issues
5. **Optimization verification**: For each optimization suggestion, verify EXPLAIN ANALYZE shows lower cost than original
6. **Schema analysis accuracy**: Run against flawed test DB — verify all planted issues detected; run against feature.lab schema — verify existing good practices recognized
7. **CLI end-to-end**: `sql-agent analyze --go-file pkg/svc/lab_features.go --db-url ... --format markdown` produces a complete report
8. **FastAPI end-to-end**: `curl -X POST /analyze -d '{"query": "SELECT * FROM lab_features"}' ` returns valid JSON report
9. **CI mode exit codes**: Critical issue → exit 1, warnings only → exit 2, clean → exit 0
10. **Docker**: `docker-compose up` starts full stack, `docker run sql-agent analyze --query "..."` works standalone

## Decisions

- **LangGraph over CrewAI**: LangGraph provides more control over state flow and conditional routing, better suited for a well-defined pipeline
- **Claude Opus 4.6**: User-specified LLM provider
- **PostgreSQL only for V1**: Reduces scope, depth over breadth
- **Live DB connection**: Enables EXPLAIN ANALYZE for actual execution metrics (not just estimated)
- **Go GORM parser as subprocess**: Clean language boundary, independently testable, can be distributed separately
- **Dedicated test database over feature.lab**: Isolates testing, allows intentionally flawed schemas, avoids dev DB pollution
- **CLI-first**: Fastest to value, easiest to test; FastAPI and CI extend same core

## Further Considerations

1. **Token cost management**: Claude Opus 4.6 is expensive. Consider caching LLM responses by (query_hash + schema_hash) to avoid repeated analysis of identical queries. Budget estimate: ~$0.50-1.00 per complex query analysis.
2. **Multi-database expansion path**: The architecture supports adding MySQL/SQLite by implementing new `db_connector` variants and updating agent prompts, but this is V2 scope.
3. **GORM V2 support**: Feature.lab uses GORM V1 (jinzhu/gorm). The parser should be designed to handle GORM V2 (`gorm.io/gorm`) as well since most new projects use V2. This is a stretch goal for Week 7-8 if time allows.
 
