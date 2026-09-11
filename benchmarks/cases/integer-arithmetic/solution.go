package main

import "fmt"

func doubleAdd(a, b int) int {
	return a*2 + b
}

func main() {
	answer := doubleAdd(20, 2)
	fmt.Println(answer)
}
