package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"log"
	"os"
)

func yamlToStruct(yamlData []byte) (Config, error) {
	var config Config
	err := yaml.Unmarshal(yamlData, &config)
	if err != nil {
		log.Fatalf("error: %v", err)
		return config, err
	}
	return config, nil
}

func getFile(fileName string) ([]byte, error) {
	data, err := os.ReadFile(fileName)
	if err != nil {
		fmt.Printf("file '%s' not found\n", fileName)
		return []byte{}, err
	}
	return data, nil
}
