package main

import "fmt"

func unrelatedAlpha(value int64) int64 { return value * 2 }
func unrelatedBeta(value int64) int64 { return value - 3 }
func unrelatedGamma(enabled bool) int64 { if enabled { return 7 }; return 9 }

type PacketSp130 struct { value int64; enabled bool }

func solve_sp_130(packet PacketSp130) int64 { if packet.enabled { return packet.value + 3 }; return packet.value }

func main() { fmt.Println(solve_sp_130(PacketSp130{value: 160, enabled: true})) }
