package main

import "fmt"

func solve_065(value int64) int64 {
	offset := int64(7)
	return step_065(value) + offset
}

func main() {
	fmt.Println(solve_065(95))
}
