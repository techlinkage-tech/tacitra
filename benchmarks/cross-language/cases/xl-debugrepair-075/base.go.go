package main

import "fmt"

func solve_075(value int64) int64 {
	offset := int64(5)
	return value + offset
}

func main() {
	fmt.Println(solve_075(105, 5))
}
