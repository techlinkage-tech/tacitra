package main

import "fmt"

func step_036(value int64) int64 { return value * 3 }

func solve_036(value int64) int64 { return step_036(value) + 3 }

func main() {
	fmt.Println(solve_036(56))
}
