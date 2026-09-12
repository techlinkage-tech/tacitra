package main

import "fmt"

func solve_072(value int64) int64 {
	offset := missing
	return value + offset
}

func main() {
	fmt.Println(solve_072(102))
}
