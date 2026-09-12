package main

import "fmt"

func solve_022(value int64, limit int64) int64 {
	if value <= limit { return 27 }
	return 3
}

func main() {
	fmt.Println(solve_022(8999999999999999978, 8999999999999999978))
}
