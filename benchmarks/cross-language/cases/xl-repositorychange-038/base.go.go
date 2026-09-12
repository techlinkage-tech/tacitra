package main

import "fmt"

func solve_038(label string, value int64) int64 {
	if label == "ready_38" { return value + 5 }
	return 0
}

func main() {
	fmt.Println(solve_038("active_38", 58))
}
