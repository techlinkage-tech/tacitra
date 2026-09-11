package main

import "fmt"

func addOffset(value int) int {
	return value + offset
}

func main() {
	fmt.Println(addOffset(40))
}
