package main

import "fmt"

type Packet020 struct { value int64; enabled bool }

func solve_020(packet Packet020) int64 {
	if packet.enabled { return packet.value + 8 }
	return packet.value
}

func main() {
	fmt.Println(solve_020(Packet020{value: 25, enabled: true}))
}
