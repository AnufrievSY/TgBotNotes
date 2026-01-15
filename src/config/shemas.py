from pydantic import BaseModel, Field

class TelegramConfig(BaseModel):
    """Конфигурация Telegram"""
    class BotConfig(BaseModel):
        """Конфигурация бота телеграм"""
        name: str = Field(..., description="Название бота")
        token: str = Field(..., description="Токен бота")
    bot: BotConfig = Field(..., description="Конфигурация бота")

class GoogleAppScriptsConfig(BaseModel):
    token: str = Field(..., description="Токен Google App Scripts")

class Config(BaseModel):
    """Конфигурация приложения"""
    telegram: TelegramConfig = Field(..., description="Конфигурация Telegram")
    gas: GoogleAppScriptsConfig = Field(..., description="Конфигурация Google App Scripts")