package parser

import (
	"go/ast"
	"go/parser"
	"go/token"
)

type GORMChain struct {
	Methods      []string `json:"methods"`
	SQLFragments []string `json:"sql_fragments"`
	File         string   `json:"file"`
	Line         int      `json:"line"`
}

type Walker struct {
	FileSet *token.FileSet
	Chains  []GORMChain
	File    string
}

func NewWalker() *Walker {
	return &Walker{
		FileSet: token.NewFileSet(),
		Chains:  []GORMChain{},
	}
}

func (w *Walker) ParseFile(filename string) error {
	w.File = filename

	file, err := parser.ParseFile(w.FileSet, filename, nil, 0)
	if err != nil {
		return err
	}

	ast.Inspect(file, w.visitNode)
	return nil
}

func (w *Walker) visitNode(node ast.Node) bool {
	if node == nil {
		return false
	}

	callExpr, ok := node.(*ast.CallExpr)
	if !ok {
		return true
	}

	chain := extractGORMChain(callExpr, w.FileSet, w.File)
	if chain != nil {
		w.Chains = append(w.Chains, *chain)
	}

	return true
}

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