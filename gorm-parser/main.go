package main

import (
	"fmt"
	"os"

	"github.com/y-infoblox/sql-optimizer-agent/gorm-parser/parser"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: gorm-parser <path-to-go-file>")
		os.Exit(1)
	}

	filename := os.Args[1]

	walker := parser.NewWalkerV2()

	err := walker.ParseFile(filename)
	if err != nil {
		fmt.Printf("Error parsing file: %v\n", err)
		os.Exit(1)
	}

	json, err := parser.EmitFullJSON(walker.Chains, walker.Warnings)
	if err != nil {
		fmt.Printf("Error generating JSON: %v\n", err)
		os.Exit(1)
	}

	fmt.Println(json)
}
