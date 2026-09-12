package main

import "fmt"

func solve_017(value int64, enabled bool) int64 {
	if enabled { return value + 5 }
	return value - 5
}

func main() {
	fmt.Println(solve_017(22, true))
}
