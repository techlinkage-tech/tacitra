package main

import "fmt"

type Packet057 struct { value int64; enabled bool }

func solve_057(packet Packet057) int64 {
	if packet.enabled { return packet.value - 4 }
	return packet.value
}

func main() {
	fmt.Println(solve_057(Packet057{value: 77, enabled: true}))
}
