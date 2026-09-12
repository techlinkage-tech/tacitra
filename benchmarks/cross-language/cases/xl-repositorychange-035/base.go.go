package main

import "fmt"

func solve_035(value int64, limit int64) int64 {
	if value < limit { return 2 }
	return 0
}

func main() {
	fmt.Println(solve_035(8999999999999999965, 8999999999999999965))
}
