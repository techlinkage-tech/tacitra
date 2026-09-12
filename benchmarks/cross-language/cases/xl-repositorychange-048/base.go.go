package main

import "fmt"

func step_048(value int64) int64 { return value * 5 }

func solve_048(value int64) int64 { return step_048(value) + 5 }

func main() {
	fmt.Println(solve_048(68))
}
