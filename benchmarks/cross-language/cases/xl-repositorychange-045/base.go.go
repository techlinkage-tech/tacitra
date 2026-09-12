package main

import "fmt"

type Packet045 struct { value int64; enabled bool }

func solve_045(packet Packet045) int64 {
	if packet.enabled { return packet.value - 2 }
	return packet.value
}

func main() {
	fmt.Println(solve_045(Packet045{value: 65, enabled: true}))
}
