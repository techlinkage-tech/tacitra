package main

import "fmt"

func solve_081(value int64) int64 {
	offset := int64(5)
	return step_081(value) + offset
}

func main() {
	fmt.Println(solve_081(111))
}
