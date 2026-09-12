package main

import "fmt"

func unrelatedAlpha(value int64) int64 { return value * 2 }
func unrelatedBeta(value int64) int64 { return value - 3 }
func unrelatedGamma(enabled bool) int64 { if enabled { return 7 }; return 9 }

func solve_sp_147(value int64, divisor int64) (int64, bool) { if divisor <= 1 { return 0, false }; return value / divisor, true }
func consume(value int64, ok bool) int64 { if ok { return value }; return -1 }

func main() { fmt.Println(consume(solve_sp_147(177, 1))) }
