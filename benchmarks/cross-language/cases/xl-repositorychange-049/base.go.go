package main

import "fmt"

func solve_049(value int64, limit int64) int64 {
	if value > limit { return value - 6 }
	return 0
}

func main() {
	fmt.Println(solve_049(69, 69))
}
