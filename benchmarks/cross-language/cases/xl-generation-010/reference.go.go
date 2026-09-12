package main

import "fmt"

func solve_010(value int64) int64 {
	offset := int64(5)
	bonus := int64(3)
	return value + offset + bonus
}

func main() {
	fmt.Println(solve_010(15))
}
