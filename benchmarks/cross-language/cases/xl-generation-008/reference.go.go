package main

import "fmt"

func step_008(value int64) int64 { return value * 2 }

func solve_008(value int64) int64 { return step_008(value) + 3 }

func main() {
	fmt.Println(solve_008(13))
}
