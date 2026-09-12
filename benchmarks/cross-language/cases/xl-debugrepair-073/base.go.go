package main

import "fmt"

func solve_073(value int64) int64 {
	offset := int64(3)
	return step_073(value) + offset
}

func main() {
	fmt.Println(solve_073(103))
}
