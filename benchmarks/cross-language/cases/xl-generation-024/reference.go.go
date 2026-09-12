package main

import "fmt"

func step_024(value int64) int64 { return value * 2 }

func solve_024(value int64) int64 { return step_024(value) + 5 }

func main() {
	fmt.Println(solve_024(29))
}
