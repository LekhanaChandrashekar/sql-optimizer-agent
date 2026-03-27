package parser

/*

import (
<<<<<<< HEAD
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

=======
	"go/ast"   // gives us AST node types like CallExpr, Ident etc
	"go/token" // gives us file position tracking (line numbers)
)

// extractGORMChain is the MAIN function
// It receives ONE function call node from ast_walker
// Returns GORMChain if it's a GORM call, nil if not
func extractGORMChain(
	call *ast.CallExpr, // the function call node
	fset *token.FileSet, // file position tracker
	file string, // which file we're parsing
) *GORMChain {

	// Step 1: Get all method names and the receiver
	// Example: db.Where("x").First(&sub)
	// methods  = ["Where", "First"]
	// receiver = db
	methods, receiver := extractMethodChain(call)

	// Step 2: Check if ANY method is a GORM method
	// If none are GORM methods → skip this call
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
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

<<<<<<< HEAD
=======
	// Step 3: Not a GORM call → return nil (skip!)
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
	if !hasGORM {
		return nil
	}

<<<<<<< HEAD
=======
	// Step 4: Check if receiver is a db variable
	// db.Where() → receiver is "db"
	// fmt.Println() → receiver is "fmt"
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
	if !isDBReceiver(receiver) {
		return nil
	}

<<<<<<< HEAD
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
=======
	// Step 5: Extract SQL fragments from Where() calls
	// db.Where("account_id = ?").First(&sub)
	// → extracts "account_id = ?"
	sqlFragments := extractSQLFragments(call)

	// Step 6: Get the line number in the file
	pos := fset.Position(call.Pos())

	// Step 7: Return the complete GORMChain!
	return &GORMChain{
		Methods:      methods,      // ["Where", "First"]
		SQLFragments: sqlFragments, // ["account_id = ?"]
		File:         file,         // "lab_features.go"
		Line:         pos.Line,     // 118
	}
}

// extractMethodChain walks backwards through the method chain
// and collects all method names
// Example: db.Where("x").First(&sub)
// Returns: methods=["Where","First"], receiver=db
func extractMethodChain(call *ast.CallExpr) ([]string, ast.Expr) {
	methods := []string{} // empty list to collect method names
	var receiver ast.Expr // will hold the final receiver (db)

	current := ast.Expr(call) // start from the outermost call

	for {
		// Check if current node is a function call
		callExpr, ok := current.(*ast.CallExpr)
		if !ok {
			break // not a function call, stop!
		}

		// Check if it has a selector (like .Where or .First)
		selector, ok := callExpr.Fun.(*ast.SelectorExpr)
		if !ok {
			break // no selector, stop!
		}

		// Add method name to FRONT of list
		// Why front? Because we walk from right to left
		// First → Where → db
		// But we want: ["Where", "First"] (left to right)
		methods = append([]string{selector.Sel.Name}, methods...)

		// Move to the left side of the chain
		current = selector.X  // moves from First → Where → db
		receiver = selector.X // tracks the final receiver
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
	}

	return methods, receiver
}

<<<<<<< HEAD
=======
// isDBReceiver checks if expression is a database variable
// We need this because not ALL method chains are GORM!
// db.Where() → YES
// fmt.Println() → NO
// os.Open() → NO
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
func isDBReceiver(expr ast.Expr) bool {
	if expr == nil {
		return false
	}

	switch e := expr.(type) {
	case *ast.Ident:
<<<<<<< HEAD
		dbNames := map[string]bool{
			"db":   true,
			"DB":   true,
			"gdb":  true,
			"conn": true,
			"tx":   true,
=======
		// Check if variable name is a known DB variable name
		dbNames := map[string]bool{
			"db":   true, // most common
			"DB":   true, // sometimes used
			"gdb":  true, // gorm db
			"conn": true, // connection
			"tx":   true, // transaction
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
		}
		return dbNames[e.Name]

	case *ast.CallExpr:
<<<<<<< HEAD
=======
		// Handle chained calls
		// db.Where().First() → receiver of First is Where()
		// → receiver of Where() is db
		// So we check recursively!
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
		if sel, ok := e.Fun.(*ast.SelectorExpr); ok {
			return isDBReceiver(sel.X)
		}
	}

	return false
}

<<<<<<< HEAD
func extractSQLFragments(call *ast.CallExpr) []string {
	fragments := []string{}

=======
// extractSQLFragments finds all WHERE conditions in the chain
// and extracts the SQL string from first argument
// Example: db.Where("account_id = ?", "16").First(&sub)
// → extracts "account_id = ?"
func extractSQLFragments(call *ast.CallExpr) []string {
	fragments := []string{} // empty list to collect SQL fragments
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
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

<<<<<<< HEAD
=======
		// Only extract from Where(), Not(), Or()
		// These are the methods that contain SQL conditions!
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
		if selector.Sel.Name == "Where" ||
			selector.Sel.Name == "Not" ||
			selector.Sel.Name == "Or" {

<<<<<<< HEAD
			if len(callExpr.Args) > 0 {
				if lit, ok := callExpr.Args[0].(*ast.BasicLit); ok {
					if lit.Kind == token.STRING {
						sql, err := strconv.Unquote(lit.Value)
						if err == nil && sql != "" {
							fragments = append(fragments, sql)
						}
					}
=======
			// Check if there are arguments
			if len(callExpr.Args) > 0 {
				// Check if first argument is a string literal
				// "account_id = ?" is a string literal
				// accountID variable is NOT a string literal
				if lit, ok := callExpr.Args[0].(*ast.BasicLit); ok {
					sql := lit.Value // gets "account_id = ?" with quotes

					// Remove the surrounding quotes
					// "account_id = ?" → account_id = ?
					if len(sql) > 2 {
						sql = sql[1 : len(sql)-1]
					}
					fragments = append(fragments, sql)
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)
				}
			}
		}

<<<<<<< HEAD
		current = selector.X
	}

	// reverse order
	for i, j := 0, len(fragments)-1; i < j; i, j = i+1, j-1 {
		fragments[i], fragments[j] = fragments[j], fragments[i]
	}

	return fragments
}
=======
		// Move to next in chain
		current = selector.X
	}

	return fragments
}
>>>>>>> ae51fdb (feat: add Go GORM parser pipeline components)

*/
