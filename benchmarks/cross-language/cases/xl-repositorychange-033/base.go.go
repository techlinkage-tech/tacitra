package main

import "fmt"

type Packet033 struct { value int64; enabled bool }

func solve_033(packet Packet033) int64 {
	if packet.enabled { return packet.value - 5 }
	return packet.value
}

func main() {
	fmt.Println(solve_033(Packet033{value: 53, enabled: true}))
}
