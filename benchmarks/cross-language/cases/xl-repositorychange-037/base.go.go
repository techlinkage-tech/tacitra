package main

import "fmt"

func solve_037(value int64, limit int64) int64 {
	if value > limit { return value - 4 }
	return 0
}

func main() {
	fmt.Println(solve_037(57, 57))
}
