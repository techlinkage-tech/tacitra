package main

import "fmt"

func solve_053(value int64, limit int64) int64 {
	if value < limit { return 5 }
	return 0
}

func main() {
	fmt.Println(solve_053(8999999999999999947, 8999999999999999947))
}
