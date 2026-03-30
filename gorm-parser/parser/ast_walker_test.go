package parser

import (
	"os"
	"testing"
)

// helper function creates a temp Go file for testing
func createTempFile(t *testing.T, content string) string {
	t.Helper()
	tmpFile, err := os.CreateTemp("", "test_*.go")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := tmpFile.WriteString(content); err != nil {
		t.Fatal(err)
	}
	tmpFile.Close()
	return tmpFile.Name()
}

// Test 1: Where() method detected correctly
func TestWhereMethod(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	var result interface{}
	db.Where("name = ?", "test").Find(&result)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	if len(walker.Chains) == 0 {
		t.Fatal("Expected chains but got none")
	}

	found := false
	for _, chain := range walker.Chains {
		for _, method := range chain.Methods {
			if method == "Where" {
				found = true
			}
		}
	}
	if !found {
		t.Fatal("Expected Where method in chains")
	}
}

// Test 2: First() method detected correctly
func TestFirstMethod(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	var result interface{}
	db.Where("id = ?", 1).First(&result)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, chain := range walker.Chains {
		for _, method := range chain.Methods {
			if method == "First" {
				found = true
			}
		}
	}
	if !found {
		t.Fatal("Expected First method in chains")
	}
}

// Test 3: Find() method detected correctly
func TestFindMethod(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	var results []interface{}
	db.Where("status = ?", "active").Find(&results)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, chain := range walker.Chains {
		for _, method := range chain.Methods {
			if method == "Find" {
				found = true
			}
		}
	}
	if !found {
		t.Fatal("Expected Find method in chains")
	}
}

// Test 4: Delete() method detected correctly
func TestDeleteMethod(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	db.Where("id = ?", 1).Delete(&struct{}{})
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, chain := range walker.Chains {
		for _, method := range chain.Methods {
			if method == "Delete" {
				found = true
			}
		}
	}
	if !found {
		t.Fatal("Expected Delete method in chains")
	}
}

// Test 5: Chained Where().First() detected correctly
func TestChainedMethods(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	var result interface{}
	db.Where("account_id = ?", "16").First(&result)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, chain := range walker.Chains {
		hasWhere := false
		hasFirst := false
		for _, method := range chain.Methods {
			if method == "Where" {
				hasWhere = true
			}
			if method == "First" {
				hasFirst = true
			}
		}
		if hasWhere && hasFirst {
			found = true
		}
	}
	if !found {
		t.Fatal("Expected chained Where+First methods")
	}
}

// Test 6: Multiple Where() conditions extracted
func TestMultipleWhereConditions(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	var results []interface{}
	db.Where("name = ?", "test").Where("status = ?", "active").Find(&results)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, chain := range walker.Chains {
		if len(chain.SQLFragments) >= 2 {
			found = true
		}
	}
	if !found {
		t.Fatal("Expected multiple SQL fragments")
	}
}

// Test 7: Non-GORM calls NOT detected
func TestNonGORMCallsIgnored(t *testing.T) {
	code := `package main
import "fmt"
func test() {
	fmt.Println("hello")
	fmt.Sprintf("world %s", "test")
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	if len(walker.Chains) > 0 {
		t.Fatalf("Expected no chains for non-GORM code, got %d", len(walker.Chains))
	}
}

// Test 8: SQL fragments extracted correctly
func TestSQLFragmentExtraction(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func test(db *gorm.DB) {
	var result interface{}
	db.Where("account_id = ?", "16").First(&result)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalker()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, chain := range walker.Chains {
		for _, fragment := range chain.SQLFragments {
			if fragment == "account_id = ?" {
				found = true
			}
		}
	}
	if !found {
		t.Fatal("Expected SQL fragment 'account_id = ?'")
	}
}
