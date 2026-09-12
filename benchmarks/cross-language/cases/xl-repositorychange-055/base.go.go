package main

import "fmt"

func solve_055(value int64, limit int64) int64 {
	if value > limit { return value - 2 }
	return 0
}

func main() {
	fmt.Println(solve_055(75, 75))
}
