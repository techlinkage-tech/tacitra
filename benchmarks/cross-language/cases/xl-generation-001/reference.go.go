package main

import "fmt"

func solve_001(value int64, enabled bool) int64 {
	if enabled { return value + 3 }
	return value - 3
}

func main() {
	fmt.Println(solve_001(6, true))
}
