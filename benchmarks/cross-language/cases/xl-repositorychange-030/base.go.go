package main

import "fmt"

func step_030(value int64) int64 { return value * 2 }

func solve_030(value int64) int64 { return step_030(value) + 2 }

func main() {
	fmt.Println(solve_030(50))
}
