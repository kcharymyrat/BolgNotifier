package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"log"
	"os"
)

type EmailServer struct {
	Host string `yaml:"host"`
	Port int    `yaml:"port"`
}

type EmailClient struct {
	Email    string `yaml:"email"`
	Password string `yaml:"password"`
	SendTo   string `yaml:"send_to"`
}

type TelegramClient struct {
	BotToken string `yaml:"bot_token"`
	Chanel   string `yaml:"channel"`
}

type Config struct {
	Mode     string         `yaml:"mode"`
	Server   EmailServer    `yaml:"server"`
	Client   EmailClient    `yaml:"client"`
	Telegram TelegramClient `yaml:"telegram"`
}

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
