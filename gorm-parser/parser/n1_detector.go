package parser

import (
    "encoding/json"
    "go/ast"
    goparser "go/parser"
    "go/token"
)

type WarningType string

const (
    WarnN1Pattern       WarningType = "N1_PATTERN"
    WarnMissingPreload  WarningType = "MISSING_PRELOAD"
    WarnLongTransaction WarningType = "LONG_TRANSACTION"
)

type Warning struct {
    Type       WarningType `json:"type"`
    Message    string      `json:"message"`
    File       string      `json:"file"`
    Line       int         `json:"line"`
    Suggestion string      `json:"suggestion"`
}

type FullOutput struct {
    Chains   []GORMChain `json:"chains"`
    Warnings []Warning   `json:"warnings"`
}

func EmitFullJSON(chains []GORMChain, warnings []Warning) (string, error) {
    out := FullOutput{Chains: chains, Warnings: warnings}
    jsonBytes, err := json.MarshalIndent(out, "", "  ")
    if err != nil {
        return "", err
    }
    return string(jsonBytes), nil
}

type WalkerV2 struct {
    Walker
    Warnings          []Warning
    insideLoop        bool
    insideTransaction bool
    txStartLine       int
    txCallCount       int
}

func NewWalkerV2() *WalkerV2 {
    return &WalkerV2{
        Walker:   Walker{FileSet: token.NewFileSet(), Chains: []GORMChain{}},
        Warnings: []Warning{},
    }
}

func (w *WalkerV2) ParseFile(filename string) error {
    w.File = filename
    file, err := goparser.ParseFile(w.FileSet, filename, nil, 0)
    if err != nil {
        return err
    }
    ast.Inspect(file, w.visitNodeV2)
    return nil
}

func (w *WalkerV2) visitNodeV2(node ast.Node) bool {
    if node == nil {
        return false
    }
    switch n := node.(type) {
    case *ast.ForStmt, *ast.RangeStmt:
        prevLoop := w.insideLoop
        w.insideLoop = true
        ast.Inspect(node, func(inner ast.Node) bool {
            if inner == nil {
                return false
            }
            if inner == node {
                return true
            }
            if callExpr, ok := inner.(*ast.CallExpr); ok {
                w.checkN1Pattern(callExpr)
                w.checkMissingPreload(callExpr)
                chain := extractGORMChain(callExpr, w.FileSet, w.File)
                if chain != nil {
                    w.Chains = append(w.Chains, *chain)
                }
            }
            return true
        })
        w.insideLoop = prevLoop
        return false
    case *ast.CallExpr:
        w.checkTransactionScope(n)
        chain := extractGORMChain(n, w.FileSet, w.File)
        if chain != nil {
            w.Chains = append(w.Chains, *chain)
        }
    }
    return true
}

func (w *WalkerV2) checkN1Pattern(call *ast.CallExpr) {
    if !w.insideLoop {
        return
    }
    methods, receiver := extractMethodChain(call)
    if !isDBReceiver(receiver) {
        return
    }
    hasWhere, hasFetch, isIDLookup := false, false, false
    for _, method := range methods {
        if method == "Where" {
            hasWhere = true
            for _, frag := range extractSQLFragments(call) {
                if containsIDPattern(frag) {
                    isIDLookup = true
                }
            }
        }
        if method == "First" || method == "Find" {
            hasFetch = true
        }
    }
    if hasWhere && hasFetch && isIDLookup {
        pos := w.FileSet.Position(call.Pos())
        w.Warnings = append(w.Warnings, Warning{
            Type:       WarnN1Pattern,
            Message:    "N+1 query detected: .Where(\"id = ?\").First() inside a loop causes one DB query per iteration",
            File:       w.File,
            Line:       pos.Line,
            Suggestion: "Use batch query: db.Where(\"id IN ?\", ids).Find(&results) outside the loop, then build a map for lookup",
        })
    }
}

func containsIDPattern(fragment string) bool {
    for _, pattern := range []string{"id = ?", "id=?", "ID = ?", "id = $"} {
        for i := 0; i <= len(fragment)-len(pattern); i++ {
            if fragment[i:i+len(pattern)] == pattern {
                return true
            }
        }
    }
    return false
}

func (w *WalkerV2) checkMissingPreload(call *ast.CallExpr) {
    if !w.insideLoop {
        return
    }
    methods, receiver := extractMethodChain(call)
    if !isDBReceiver(receiver) {
        return
    }
    hasFind, hasPreload, hasJoins := false, false, false
    for _, method := range methods {
        if method == "Find" || method == "First" {
            hasFind = true
        }
        if method == "Preload" {
            hasPreload = true
        }
        if method == "Joins" {
            hasJoins = true
        }
    }
    if hasFind && !hasPreload && !hasJoins {
        pos := w.FileSet.Position(call.Pos())
        w.Warnings = append(w.Warnings, Warning{
            Type:       WarnMissingPreload,
            Message:    "Missing .Preload(): fetching records inside a loop without Preload() causes N+1 queries",
            File:       w.File,
            Line:       pos.Line,
            Suggestion: "Add .Preload(\"AssociationName\") before .Find() to eagerly load related records in one query",
        })
    }
}

func (w *WalkerV2) checkTransactionScope(call *ast.CallExpr) {
    sel, ok := call.Fun.(*ast.SelectorExpr)
    if !ok {
        return
    }
    methodName := sel.Sel.Name
    pos := w.FileSet.Position(call.Pos())
    if methodName == "Begin" && isDBReceiver(sel.X) {
        w.insideTransaction = true
        w.txStartLine = pos.Line
        w.txCallCount = 0
    }
    if w.insideTransaction && isGORMMethod(methodName) {
        w.txCallCount++
        if w.txCallCount > 5 {
            w.Warnings = append(w.Warnings, Warning{
                Type:       WarnLongTransaction,
                Message:    "Long-held transaction: more than 5 DB operations in a single transaction increases lock contention risk",
                File:       w.File,
                Line:       w.txStartLine,
                Suggestion: "Break large transactions into smaller units. Only wrap operations that truly need atomicity.",
            })
            w.txCallCount = -999
        }
    }
    if (methodName == "Commit" || methodName == "Rollback") && w.insideTransaction {
        w.insideTransaction = false
        w.txCallCount = 0
    }
}
