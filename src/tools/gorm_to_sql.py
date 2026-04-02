
# Mapping of GORM terminal methods to SQL statement types
_READ_METHODS = {"First", "Find", "Last", "Take", "Scan", "Count", "Pluck"}
_WRITE_METHODS = {"Create", "Save", "Updates", "Update", "Delete"}


def _build_select(chain: dict) -> str:
    methods = chain.get("methods", [])
    fragments = chain.get("sql_fragments", [])

    # Determine table from methods or default
    table = "unknown_table"

    # Build SELECT clause
    select_cols = "*"
    for m in methods:
        if m == "Select" and fragments:
            # Select method typically takes column list as first fragment
            pass  # handled via sql_fragments

    # Build WHERE clause
    where_parts = []
    for frag in fragments:
        where_parts.append(frag)

    # Build ORDER BY
    order_clause = ""
    limit_clause = ""
    offset_clause = ""
    join_clause = ""

    query = f"SELECT {select_cols} FROM {table}"
    if join_clause:
        query += f" {join_clause}"
    if where_parts:
        query += f" WHERE {' AND '.join(where_parts)}"
    if order_clause:
        query += f" ORDER BY {order_clause}"
    if limit_clause:
        query += f" LIMIT {limit_clause}"
    if offset_clause:
        query += f" OFFSET {offset_clause}"

    return query


def _build_write(chain: dict, stmt_type: str) -> str:
    fragments = chain.get("sql_fragments", [])
    table = "unknown_table"

    if stmt_type == "Create":
        return f"INSERT INTO {table} VALUES (...)"
    elif stmt_type == "Delete":
        where = f" WHERE {' AND '.join(fragments)}" if fragments else ""
        return f"DELETE FROM {table}{where}"
    elif stmt_type in ("Updates", "Update", "Save"):
        where = f" WHERE {' AND '.join(fragments)}" if fragments else ""
        return f"UPDATE {table} SET ...{where}"

    return f"-- Unknown write: {stmt_type}"


def convert_gorm_output_to_sql(gorm_output: dict) -> list:
    queries = []

    for chain in gorm_output.get("chains", []):
        methods = chain.get("methods", [])

        # Determine statement type from the terminal method
        stmt_type = None
        for m in methods:
            if m in _READ_METHODS:
                stmt_type = "SELECT"
                break
            if m in _WRITE_METHODS:
                stmt_type = m
                break

        if stmt_type == "SELECT":
            queries.append({
                "sql": _build_select(chain),
                "file": chain.get("file", ""),
                "line": chain.get("line", 0),
                "methods": methods,
                "type": "SELECT",
            })
        elif stmt_type:
            queries.append({
                "sql": _build_write(chain, stmt_type),
                "file": chain.get("file", ""),
                "line": chain.get("line", 0),
                "methods": methods,
                "type": stmt_type.upper(),
            })

    return queries