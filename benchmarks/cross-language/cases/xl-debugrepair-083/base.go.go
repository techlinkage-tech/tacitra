package main

import "fmt"

func solve_083(value int64) int64 {
	offset := int64(7)
	return value + offset
}

func main() {
	fmt.Println(solve_083(113, 7))
}
