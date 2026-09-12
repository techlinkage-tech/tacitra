package main

import "fmt"

func solve_025(value int64, enabled bool) int64 {
	if enabled { return value + 6 }
	return value - 6
}

func main() {
	fmt.Println(solve_025(30, true))
}
