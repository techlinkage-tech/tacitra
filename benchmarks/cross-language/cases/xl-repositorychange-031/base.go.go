package main

import "fmt"

func solve_031(value int64, limit int64) int64 {
	if value > limit { return value - 3 }
	return 0
}

func main() {
	fmt.Println(solve_031(51, 51))
}
