package main

import "fmt"

func solve_018(value int64) int64 {
	offset := int64(6)
	bonus := int64(3)
	return value + offset + bonus
}

func main() {
	fmt.Println(solve_018(23))
}
