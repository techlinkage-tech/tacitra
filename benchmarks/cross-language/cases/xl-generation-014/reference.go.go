package main

import "fmt"

func solve_014(value int64, limit int64) int64 {
	if value <= limit { return 19 }
	return 2
}

func main() {
	fmt.Println(solve_014(8999999999999999986, 8999999999999999986))
}
