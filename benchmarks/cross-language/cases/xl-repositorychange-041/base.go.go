package main

import "fmt"

func solve_041(value int64, limit int64) int64 {
	if value < limit { return 3 }
	return 0
}

func main() {
	fmt.Println(solve_041(8999999999999999959, 8999999999999999959))
}
