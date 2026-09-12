package main

import "fmt"

func solve_079(value int64) int64 {
	offset := int64(3)
	return value + offset
}

func main() {
	fmt.Println(solve_079(109, 3))
}
