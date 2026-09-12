package main

import "fmt"

func solve_061(value int64) int64 {
	offset := int64(3)
	return step_061(value) + offset
}

func main() {
	fmt.Println(solve_061(91))
}
