package main

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
