package main

import "fmt"

func step_042(value int64) int64 { return value * 4 }

func solve_042(value int64) int64 { return step_042(value) + 4 }

func main() {
	fmt.Println(solve_042(62))
}
