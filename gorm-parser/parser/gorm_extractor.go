package parser

/*

import (
	"go/ast"
	"go/token"
	"strconv"
)
func extractGORMChain(call *ast.CallExpr, fset *token.FileSet, file string) *GORMChain {
	methods, receiver := extractMethodChain(call)

	hasGORM := false
	for _, method := range methods {
		if isGORMMethod(method) {
			hasGORM = true
			break
		}
	}

	if !hasGORM {
		return nil
	}

	if !isDBReceiver(receiver) {
		return nil
	}

	sqlFragments := extractSQLFragments(call)
	pos := fset.Position(call.Pos())

	return &GORMChain{
		Methods:      methods,
		SQLFragments: sqlFragments,
		File:         file,
		Line:         pos.Line,
	}
}

func extractMethodChain(call *ast.CallExpr) ([]string, ast.Expr) {
	methods := []string{}
	var receiver ast.Expr

	current := ast.Expr(call)

	for {
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break
		}

		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break
		}

		methods = append([]string{selector.Sel.Name}, methods...)
		current = selector.X
		receiver = selector.X
	}

	return methods, receiver
}

func isDBReceiver(expr ast.Expr) bool {
	if expr == nil {
		return false
	}

	switch e := expr.(type) {
	case *ast.Ident:
		dbNames := map[string]bool{
			"db":   true,
			"DB":   true,
			"gdb":  true,
			"conn": true,
			"tx":   true,
		}
		return dbNames[e.Name]

	case *ast.CallExpr:
		if sel, ok := e.Fun.(*ast.SelectorExpr); ok {
			return isDBReceiver(sel.X)
		}
	}

	return false
}

func extractSQLFragments(call *ast.CallExpr) []string {
	fragments := []string{}
	current := ast.Expr(call)

	for {
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break
		}

		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break
		}

		if selector.Sel.Name == "Where" ||
			selector.Sel.Name == "Not" ||
			selector.Sel.Name == "Or" {
			if len(callExpr.Args) > 0 {
				if lit, ok := callExpr.Args[0].(*ast.BasicLit); ok {
					if lit.Kind == token.STRING {
						sql, err := strconv.Unquote(lit.Value)
						if err == nil && sql != "" {
							fragments = append(fragments, sql)
						}
					}
				}
			}
		}

		current = selector.X
	}

	for i, j := 0, len(fragments)-1; i < j; i, j = i+1, j-1 {
		fragments[i], fragments[j] = fragments[j], fragments[i]
	}

	return fragments
}

func extractGORMChain(call *ast.CallExpr, fset *token.FileSet, file string) *GORMChain {
	methods, receiver := extractMethodChain(call)

*/

import (
	"go/ast"
	"go/token"
	"strconv"
)

func extractGORMChain(call *ast.CallExpr, fset *token.FileSet, file string) *GORMChain {
	methods, receiver := extractMethodChain(call)

	hasGORM := false
	for _, method := range methods {
		if isGORMMethod(method) {
			hasGORM = true
			break
		}
	}

	if !hasGORM || !isDBReceiver(receiver) {
		return nil
	}

	sqlFragments := extractSQLFragments(call)
	pos := fset.Position(call.Pos())

	return &GORMChain{
		Methods:      methods,
		SQLFragments: sqlFragments,
		File:         file,
		Line:         pos.Line,
	}
}

func extractMethodChain(call *ast.CallExpr) ([]string, ast.Expr) {
	methods := []string{}
	var receiver ast.Expr

	current := ast.Expr(call)
	for {
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break
		}

		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break
		}

		methods = append([]string{selector.Sel.Name}, methods...)
		current = selector.X
		receiver = selector.X
	}

	return methods, receiver
}

func isDBReceiver(expr ast.Expr) bool {
	if expr == nil {
		return false
	}

	switch e := expr.(type) {
	case *ast.Ident:
		dbNames := map[string]bool{
			"db":   true,
			"DB":   true,
			"gdb":  true,
			"conn": true,
			"tx":   true,
		}
		return dbNames[e.Name]
	case *ast.CallExpr:
		if sel, ok := e.Fun.(*ast.SelectorExpr); ok {
			return isDBReceiver(sel.X)
		}
	}

	return false
}

func extractSQLFragments(call *ast.CallExpr) []string {
	fragments := []string{}
	current := ast.Expr(call)

	for {
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break
		}

		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break
		}

		if selector.Sel.Name == "Where" || selector.Sel.Name == "Not" || selector.Sel.Name == "Or" {
			if len(callExpr.Args) > 0 {
				if lit, ok := callExpr.Args[0].(*ast.BasicLit); ok && lit.Kind == token.STRING {
					sql, err := strconv.Unquote(lit.Value)
					if err == nil && sql != "" {
						fragments = append(fragments, sql)
					}
				}
			}
		}

		current = selector.X
	}

	for i, j := 0, len(fragments)-1; i < j; i, j = i+1, j-1 {
		fragments[i], fragments[j] = fragments[j], fragments[i]
	}

	return fragments
}

/*
	hasGORM := false
	for _, method := range methods {
		if isGORMMethod(method) {
			hasGORM = true
			break
		}
	}

	if !hasGORM {
		return nil
	}

	if !isDBReceiver(receiver) {
		return nil
	}

	sqlFragments := extractSQLFragments(call)

	pos := fset.Position(call.Pos())

	return &GORMChain{
		Methods:      methods,
		SQLFragments: sqlFragments,
		File:         file,
		Line:         pos.Line,
	}
}

func extractMethodChain(call *ast.CallExpr) ([]string, ast.Expr) {
	methods := []string{}
	var receiver ast.Expr

	current := ast.Expr(call)

	for {
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break
		}

		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break
		}

		methods = append([]string{selector.Sel.Name}, methods...)

		current = selector.X
		receiver = selector.X
	}

	return methods, receiver
}

func isDBReceiver(expr ast.Expr) bool {
	if expr == nil {
		return false
	}

	switch e := expr.(type) {
	case *ast.Ident:
		dbNames := map[string]bool{
			"db":   true,
			"DB":   true,
			"gdb":  true,
			"conn": true,
			"tx":   true,
		}
		return dbNames[e.Name]

	case *ast.CallExpr:
		if sel, ok := e.Fun.(*ast.SelectorExpr); ok {
			return isDBReceiver(sel.X)
		}
	}

	return false
}

func extractSQLFragments(call *ast.CallExpr) []string {
	fragments := []string{}

	current := ast.Expr(call)

	for {
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break
		}

		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break
		}

		if selector.Sel.Name == "Where" ||
			selector.Sel.Name == "Not" ||
			selector.Sel.Name == "Or" {


			if len(callExpr.Args) > 0 {
				if lit, ok := callExpr.Args[0].(*ast.BasicLit); ok {
					if lit.Kind == token.STRING {
						sql, err := strconv.Unquote(lit.Value)
						if err == nil && sql != "" {
							fragments = append(fragments, sql)
						}
					}

			// Check if there are arguments
			if len(callExpr.Args) > 0 {
				// Check if first argument is a string literal
				// "account_id = ?" is a string literal
				// accountID variable is NOT a string literal
				if lit, ok := callExpr.Args[0].(*ast.BasicLit); ok {
					if lit.Kind == token.STRING {
						sql, err := strconv.Unquote(lit.Value)
						if err == nil && sql != "" {
							fragments = append(fragments, sql)
						}
					}

					fragments = append(fragments, sql)
 ae51fdb (feat: add Go GORM parser pipeline components)

 e50a772 (fix: apply Copilot suggestions - strconv.Unquote and fragment order)
				}
			}
		}

		current = selector.X
	}

	// reverse order
	for i, j := 0, len(fragments)-1; i < j; i, j = i+1, j-1 {
		fragments[i], fragments[j] = fragments[j], fragments[i]
	}

	return fragments
}

*/
