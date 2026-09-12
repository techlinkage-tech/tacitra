package main

import "fmt"

func solve_076(value int64) int64 {
	offset := missing
	return value + offset
}

func main() {
	fmt.Println(solve_076(106))
}
