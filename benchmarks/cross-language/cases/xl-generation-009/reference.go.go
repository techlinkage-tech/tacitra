package main

import "fmt"

func solve_009(value int64, enabled bool) int64 {
	if enabled { return value + 4 }
	return value - 4
}

func main() {
	fmt.Println(solve_009(14, true))
}
