package main

import "fmt"

func step_016(value int64) int64 { return value * 2 }

func solve_016(value int64) int64 { return step_016(value) + 4 }

func main() {
	fmt.Println(solve_016(21))
}
