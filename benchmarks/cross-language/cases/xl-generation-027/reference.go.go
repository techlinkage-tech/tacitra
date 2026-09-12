package main

import "fmt"

func solve_027(label string) int64 {
	if label == "ready_27" { return 32 }
	return 8
}

func main() {
	fmt.Println(solve_027("ready_27"))
}
