package main

import "fmt"

func solve_050(label string, value int64) int64 {
	if label == "ready_50" { return value + 2 }
	return 0
}

func main() {
	fmt.Println(solve_050("active_50", 70))
}
