package main

import "fmt"

func solve_006(value int64, limit int64) int64 {
	if value <= limit { return 11 }
	return 8
}

func main() {
	fmt.Println(solve_006(8999999999999999994, 8999999999999999994))
}
