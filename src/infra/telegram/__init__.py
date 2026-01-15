import time
import requests.exceptions
from telebot import TeleBot, types

from src.config import log, config

from src.infra.telegram import msg_handler
from src.infra.telegram import edit_constants
from src.infra.telegram import reply_playlist_handler


def set_commands(bot: TeleBot) -> None:
    """
    Команды в выпадающем меню.
    """
    commands_private = [
        types.BotCommand("edit_constants", "Константы"),
    ]

    bot.set_my_commands(commands_private, scope=types.BotCommandScopeAllPrivateChats())

    # если надо отдельно для групп — добавь/убери
    commands_group = [
        types.BotCommand("constants", "Константы"),
    ]
    bot.set_my_commands(commands_group, scope=types.BotCommandScopeAllGroupChats())

def build_bot() -> TeleBot:
    token = config.telegram.bot.token
    bot = TeleBot(token, parse_mode="HTML")

    edit_constants.register(bot)

    reply_playlist_handler.register(bot)

    msg_handler.register(bot)

    set_commands(bot)

    return bot


def run_polling(bot: TeleBot) -> None:
    """
    Аккуратный polling с авторестартом, без бесконечной простыни.
    """
    while True:
        try:
            log.info("Bot started. Polling...")
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            log.warning("ReadTimeout: restart...")
            bot.stop_polling()
            time.sleep(3)
        except requests.exceptions.ConnectionError:
            log.warning("ConnectionError: restart...")
            bot.stop_polling()
            time.sleep(5)
        except KeyboardInterrupt:
            log.info("Stopped by Ctrl+C.")
            bot.stop_polling()
            break
        except Exception:
            log.error("Bot crashed, restarting...", exc_info=True)
            bot.stop_polling()
            time.sleep(3)


def main() -> None:
    bot = build_bot()
    run_polling(bot)


if __name__ == "__main__":
    main()
