package main

import "fmt"

func solve_005(value int64, divisor int64) (int64, bool) {
	if divisor == 0 { return 0, false }
	return value / divisor, true
}

func consume(value int64, ok bool) int64 {
	if ok { return value }
	return -1
}

func main() {
	fmt.Println(consume(solve_005(70, 7)))
}
