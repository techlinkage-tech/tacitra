package main

import "fmt"

func solve_040(value int64, divisor int64) (int64, bool) {
	if divisor <= 1 { return 0, false }
	return value / divisor, true
}

func consume(value int64, ok bool) int64 {
	if ok { return value }
	return -1
}

func main() {
	fmt.Println(consume(solve_040(60, 1)))
}
