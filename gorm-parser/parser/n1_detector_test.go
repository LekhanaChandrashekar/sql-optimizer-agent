package parser

import (
	"encoding/json"
	"os"
	"testing"
)

// ─────────────────────────────────────────────
// Integration Test 1: N+1 pattern SHOULD flag
// ─────────────────────────────────────────────

func TestN1PatternDetected(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func fetchOrders(db *gorm.DB, ids []int) {
	for _, id := range ids {
		var order Order
		db.Where("id = ?", id).First(&order)
	}
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, w := range walker.Warnings {
		if w.Type == WarnN1Pattern {
			found = true
		}
	}
	if !found {
		t.Fatal("Expected N1_PATTERN warning but got none")
	}
}

// ─────────────────────────────────────────────
// Integration Test 2: Bulk fetch + map SHOULD pass (no N+1 warning)
// ─────────────────────────────────────────────

func TestBulkFetchMapPatternPasses(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func fetchOrdersBulk(db *gorm.DB, ids []int) map[int]Order {
	var orders []Order
	db.Where("id IN ?", ids).Find(&orders)
	result := make(map[int]Order)
	for _, o := range orders {
		result[o.ID] = o
	}
	return result
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	for _, w := range walker.Warnings {
		if w.Type == WarnN1Pattern {
			t.Fatalf("Bulk fetch + map pattern should NOT trigger N+1 warning, but got: %s", w.Message)
		}
	}
}

// ─────────────────────────────────────────────
// Integration Test 3: Missing Preload SHOULD flag
// ─────────────────────────────────────────────

func TestMissingPreloadDetected(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func fetchUsers(db *gorm.DB) {
	var users []User
	for i := 0; i < 10; i++ {
		var user User
		db.Find(&user)
		users = append(users, user)
	}
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, w := range walker.Warnings {
		if w.Type == WarnMissingPreload {
			found = true
		}
	}
	if !found {
		t.Fatal("Expected MISSING_PRELOAD warning but got none")
	}
}

// ─────────────────────────────────────────────
// Integration Test 4: Preload present SHOULD pass
// ─────────────────────────────────────────────

func TestPreloadPresentPasses(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func fetchUsersWithPreload(db *gorm.DB) {
	var users []User
	db.Preload("Orders").Find(&users)
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	for _, w := range walker.Warnings {
		if w.Type == WarnMissingPreload {
			t.Fatalf("Preload present should NOT trigger MISSING_PRELOAD warning")
		}
	}
}

// ─────────────────────────────────────────────
// Integration Test 5: Long transaction SHOULD flag
// ─────────────────────────────────────────────

func TestLongTransactionDetected(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func longTx(db *gorm.DB) {
	tx := db.Begin()
	tx.Where("id = ?", 1).First(&User{})
	tx.Where("id = ?", 2).First(&Order{})
	tx.Where("id = ?", 3).First(&Order{})
	tx.Save(&User{})
	tx.Save(&Order{})
	tx.Delete(&Order{})
	tx.Commit()
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	found := false
	for _, w := range walker.Warnings {
		if w.Type == WarnLongTransaction {
			found = true
		}
	}
	if !found {
		t.Fatal("Expected LONG_TRANSACTION warning but got none")
	}
}

// ─────────────────────────────────────────────
// Integration Test 6: Short transaction SHOULD pass
// ─────────────────────────────────────────────

func TestShortTransactionPasses(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func shortTx(db *gorm.DB) {
	tx := db.Begin()
	tx.Save(&User{})
	tx.Save(&Order{})
	tx.Commit()
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	for _, w := range walker.Warnings {
		if w.Type == WarnLongTransaction {
			t.Fatalf("Short transaction should NOT trigger LONG_TRANSACTION warning")
		}
	}
}

// ─────────────────────────────────────────────
// Integration Test 7: Non-GORM code SHOULD produce no warnings
// ─────────────────────────────────────────────

func TestNonGORMCodeNoWarnings(t *testing.T) {
	code := `package main
import "fmt"
func test() {
	for i := 0; i < 10; i++ {
		fmt.Println(i)
	}
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	if len(walker.Warnings) > 0 {
		t.Fatalf("Non-GORM code should produce no warnings, got %d", len(walker.Warnings))
	}
}

// ─────────────────────────────────────────────
// Integration Test 8: JSON output includes warnings
// ─────────────────────────────────────────────

func TestJSONOutputIncludesWarnings(t *testing.T) {
	code := `package main
import "gorm.io/gorm"
func fetchOrders(db *gorm.DB, ids []int) {
	for _, id := range ids {
		var order Order
		db.Where("id = ?", id).First(&order)
	}
}`
	filename := createTempFile(t, code)
	defer os.Remove(filename)

	walker := NewWalkerV2()
	err := walker.ParseFile(filename)
	if err != nil {
		t.Fatalf("ParseFile failed: %v", err)
	}

	jsonOutput, err := EmitFullJSON(walker.Chains, walker.Warnings)
	if err != nil {
		t.Fatalf("EmitFullJSON failed: %v", err)
	}

	var output FullOutput
	if err := json.Unmarshal([]byte(jsonOutput), &output); err != nil {
		t.Fatalf("Failed to parse JSON output: %v", err)
	}

	if len(output.Warnings) == 0 {
		t.Fatal("Expected warnings in JSON output but got none")
	}

	if len(output.Chains) == 0 {
		t.Fatal("Expected chains in JSON output but got none")
	}
}
