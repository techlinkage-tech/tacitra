package main

import "fmt"

func solve_077(value int64) int64 {
	offset := int64(7)
	return step_077(value) + offset
}

func main() {
	fmt.Println(solve_077(107))
}
