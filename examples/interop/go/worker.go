package main

import (
	"encoding/json"
	"os"
)

type Request struct {
	JSONRPC string         `json:"jsonrpc"`
	ID      int            `json:"id"`
	Method  string         `json:"method"`
	Params  map[string]int `json:"params"`
}

func main() {
	var request Request
	if json.NewDecoder(os.Stdin).Decode(&request) != nil {
		os.Exit(2)
	}
	response := map[string]any{
		"jsonrpc": "2.0",
		"id":      request.ID,
		"result":  request.Params["left"] + request.Params["right"],
		"meta": map[string]any{
			"effects":      []string{},
			"capabilities": []string{},
		},
	}
	_ = json.NewEncoder(os.Stdout).Encode(response)
}
