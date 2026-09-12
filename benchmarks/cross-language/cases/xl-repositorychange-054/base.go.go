package main

import "fmt"

func step_054(value int64) int64 { return value * 6 }

func solve_054(value int64) int64 { return step_054(value) + 6 }

func main() {
	fmt.Println(solve_054(74))
}
