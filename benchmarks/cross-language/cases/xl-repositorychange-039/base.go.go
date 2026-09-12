package main

import "fmt"

type Packet039 struct { value int64; enabled bool }

func solve_039(packet Packet039) int64 {
	if packet.enabled { return packet.value - 6 }
	return packet.value
}

func main() {
	fmt.Println(solve_039(Packet039{value: 59, enabled: true}))
}
