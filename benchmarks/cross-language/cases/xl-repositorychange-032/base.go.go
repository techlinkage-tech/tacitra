package main

import "fmt"

func solve_032(label string, value int64) int64 {
	if label == "ready_32" { return value + 4 }
	return 0
}

func main() {
	fmt.Println(solve_032("active_32", 52))
}
