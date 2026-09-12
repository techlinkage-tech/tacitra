package main

import "fmt"

func solve_015(left int64, right int64, enabled bool) int64 {
	if enabled && left > 0 { return left + right }
	return 0
}

func main() {
	fmt.Println(solve_015(20, 3, true))
}
