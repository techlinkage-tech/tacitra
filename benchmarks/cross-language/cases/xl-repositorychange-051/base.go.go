package main

import "fmt"

type Packet051 struct { value int64; enabled bool }

func solve_051(packet Packet051) int64 {
	if packet.enabled { return packet.value - 3 }
	return packet.value
}

func main() {
	fmt.Println(solve_051(Packet051{value: 71, enabled: true}))
}
