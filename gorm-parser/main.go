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

	args := os.Args[1:]
	if len(args) > 0 && args[0] == "--" {
		args = args[1:]
	}
	if len(args) < 1 {
		fmt.Println("Usage: gorm-parser <path-to-go-file>")
		os.Exit(1)
	}

	filename := args[0]

	walker := parser.NewWalker()

	err := walker.ParseFile(filename)
	if err != nil {
		fmt.Printf("Error parsing file: %v\n", err)
		os.Exit(1)
	}

	jsonOutput, err := parser.EmitJSON(walker.Chains)
	if err != nil {
		fmt.Printf("Error generating JSON: %v\n", err)
		os.Exit(1)
	}

	fmt.Println(jsonOutput)
}