package main

import "fmt"

func solve_056(label string, value int64) int64 {
	if label == "ready_56" { return value + 3 }
	return 0
}

func main() {
	fmt.Println(solve_056("active_56", 76))
}
