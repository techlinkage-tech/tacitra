package main

import "fmt"

type Packet028 struct { value int64; enabled bool }

func solve_028(packet Packet028) int64 {
	if packet.enabled { return packet.value + 2 }
	return packet.value
}

func main() {
	fmt.Println(solve_028(Packet028{value: 33, enabled: true}))
}
