package main

import "fmt"

func solve_067(value int64) int64 {
	offset := int64(3)
	return value + offset
}

func main() {
	fmt.Println(solve_067(97, 3))
}
