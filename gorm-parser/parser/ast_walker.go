package parser

import (
	"go/ast"
	"go/parser"
	"go/token"
)

// GORMChain stores one GORM method chain found in code
type GORMChain struct {
	Methods      []string `json:"methods"`
	SQLFragments []string `json:"sql_fragments"`
	File         string   `json:"file"`
	Line         int      `json:"line"`
}

// Walker walks through Go AST and finds GORM chains
type Walker struct {
	FileSet *token.FileSet
	Chains  []GORMChain
	File    string
}

// NewWalker creates a new Walker
func NewWalker() *Walker {
	return &Walker{
		FileSet: token.NewFileSet(),
		Chains:  []GORMChain{},
	}
}

// ParseFile reads a Go file and walks its AST
func (w *Walker) ParseFile(filename string) error {
	w.File = filename

	// Step 1: Parse the file into AST
	file, err := parser.ParseFile(w.FileSet, filename, nil, 0)
	if err != nil {
		return err
	}

	// Step 2: Walk every node in AST
	ast.Inspect(file, w.visitNode)
	return nil
}

// visitNode is called for EVERY node in the AST tree
func (w *Walker) visitNode(node ast.Node) bool {
	// If node is empty, stop
	if node == nil {
		return false
	}

	// Check if this node is a function call
	callExpr, ok := node.(*ast.CallExpr)
	if !ok {
		// Not a function call, skip but continue walking
		return true
	}

	// Check if this is a GORM method chain
	chain := extractGORMChain(callExpr, w.FileSet, w.File)
	if chain != nil {
		w.Chains = append(w.Chains, *chain)
	}

	return true
}

// isGORMMethod checks if method name is a GORM method
func isGORMMethod(name string) bool {
	gormMethods := map[string]bool{
		"Where":   true,
		"First":   true,
		"Find":    true,
		"Create":  true,
		"Save":    true,
		"Updates": true,
		"Delete":  true,
		"Not":     true,
		"Or":      true,
		"Joins":   true,
		"Preload": true,
		"Select":  true,
		"Order":   true,
		"Limit":   true,
		"Offset":  true,
	}
	return gormMethods[name]
}
