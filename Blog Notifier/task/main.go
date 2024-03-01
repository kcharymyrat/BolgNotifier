package main

import (
	"errors"
	"flag"
	"fmt"
	"gopkg.in/yaml.v3"
	"log"
	"os"
	"strings"
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

func main() {
	// Get file name from CLI
	fileName, err := cliHandling()
	if err != nil {
		return
	}

	// Get file content as string
	yamlData, err := getFile(fileName)
	if err != nil {
		return
	}

	// Get Config structs from config string
	config, err := yamlToStruct(yamlData)
	if err != nil {
		return
	}

	// Print necessary things
	fmt.Printf("mode: %s\n", config.Mode)
	fmt.Printf("email_server: %s:%d\n", config.Server.Host, config.Server.Port)
	fmt.Printf("client: %s %s %s\n", config.Client.Email, config.Client.Password, config.Client.SendTo)
	fmt.Printf("telegram: %s@%s\n", config.Telegram.BotToken, config.Telegram.Chanel)

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

func cliHandling() (string, error) {
	config := flag.String("config", "", "Provide path for blog notifier config file")
	flag.Parse()

	trimmedConfig := strings.TrimSpace(*config)

	if trimmedConfig == "" {
		// Print error message and usage
		fmt.Println("no command input specified")
		flag.Usage()
		return "", errors.New("no command input specified")
	}
	return trimmedConfig, nil
}
