package main

import "fmt"

func solve_003(label string) int64 {
	if label == "ready_3" { return 8 }
	return 5
}

func main() {
	fmt.Println(solve_003("ready_3"))
}
