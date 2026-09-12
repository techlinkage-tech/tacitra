package main

import "fmt"

func unrelatedAlpha(value int64) int64 { return value * 2 }
func unrelatedBeta(value int64) int64 { return value - 3 }
func unrelatedGamma(enabled bool) int64 { if enabled { return 7 }; return 9 }

type PacketSp02 struct { value int64; enabled bool }

func solve_sp_02(packet PacketSp02) int64 { if packet.enabled { return packet.value + 3 }; return packet.value }

func main() { fmt.Println(solve_sp_02(PacketSp02{value: 32, enabled: true})) }
