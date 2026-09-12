package main

import "fmt"

type Packet012 struct { value int64; enabled bool }

func solve_012(packet Packet012) int64 {
	if packet.enabled { return packet.value + 7 }
	return packet.value
}

func main() {
	fmt.Println(solve_012(Packet012{value: 17, enabled: true}))
}
