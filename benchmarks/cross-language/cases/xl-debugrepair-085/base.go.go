package main

import "fmt"

func solve_085(value int64) int64 {
	offset := int64(3)
	return step_085(value) + offset
}

func main() {
	fmt.Println(solve_085(115))
}
