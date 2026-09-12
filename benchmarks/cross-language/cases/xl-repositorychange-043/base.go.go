package main

import "fmt"

func solve_043(value int64, limit int64) int64 {
	if value > limit { return value - 5 }
	return 0
}

func main() {
	fmt.Println(solve_043(63, 63))
}
