package main

import "fmt"

func solve_047(value int64, limit int64) int64 {
	if value < limit { return 4 }
	return 0
}

func main() {
	fmt.Println(solve_047(8999999999999999953, 8999999999999999953))
}
