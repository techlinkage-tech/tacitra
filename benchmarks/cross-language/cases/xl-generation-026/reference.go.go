package main

import "fmt"

func solve_026(value int64) int64 {
	offset := int64(7)
	bonus := int64(3)
	return value + offset + bonus
}

func main() {
	fmt.Println(solve_026(31))
}
