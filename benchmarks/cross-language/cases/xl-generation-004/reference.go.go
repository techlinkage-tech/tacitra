package main

import "fmt"

type Packet004 struct { value int64; enabled bool }

func solve_004(packet Packet004) int64 {
	if packet.enabled { return packet.value + 6 }
	return packet.value
}

func main() {
	fmt.Println(solve_004(Packet004{value: 9, enabled: true}))
}
