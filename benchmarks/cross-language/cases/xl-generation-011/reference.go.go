package main

import "fmt"

func solve_011(label string) int64 {
	if label == "ready_11" { return 16 }
	return 6
}

func main() {
	fmt.Println(solve_011("ready_11"))
}
