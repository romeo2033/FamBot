import logging

from bot_setup import bot  # единый экземпляр бота
import handlers  # noqa: F401  # импорт нужен для регистрации хендлеров через декораторы


logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()