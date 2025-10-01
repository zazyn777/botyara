import os
import logging
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import random
from flask import Flask
from threading import Thread

# Создаем Flask приложение для health checks
app = Flask(__name__)


@app.route('/')
def home():
    return "🦫 Бобр-бот работает!", 200


@app.route('/health')
def health():
    return "OK", 200


def run_flask():
    """Запускает Flask сервер в отдельном потоке"""
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


# Настройки из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Не заданы BOT_TOKEN или CHAT_ID в переменных окружения")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем приложение один раз
application = Application.builder().token(BOT_TOKEN).build()

# Храним ID всех сообщений бота за день
last_message_ids = []

# Коллекция эмодзи и вариантов для разнообразия
MORNING_GREETINGS = [
    "🌅 С бобрым утром!",
    "🦫 С бобрым утром!",
    "☀️ С бобрым утром!",
    "🌞 С бобрым утром!",
    "😊 С бобрым утром!",
    "🌟 С бобрым утром!",
    "💫 С бобрым утром!",
    "🪵 С бобрым утром!"
]

OTHER_OPTIONS = [
    "🌈 Я гей",
    "🎭 Я пидр",
    "💅 Я чмо",
    "✨ Я хуесос",
    "🦄 Я пидорас",
    "🎪 Я женя"
]

FUNNY_DESCRIPTIONS = [
    "Проснись и пой моргенштерна 🎵?",
    "Утро добрым не бывает? 🐾\nКоля нахуй посылает",
    "Заведи моторчик! 🚗\nПодрочи",
    "Кофе готов? ☕️\nА срать?",
    "Новый день - новые победы! 🏆\nРегни катку в кс",
    "Бобры уже трудятся! 🦫\nА пидр",
    "Солнце встает 🌞\nНахуй ты встал?"
]


async def delete_previous_messages():
    """Удаляет все предыдущие сообщения бота"""
    global last_message_ids

    if not last_message_ids:
        return

    successful_deletes = 0
    for message_id in last_message_ids:
        try:
            await application.bot.delete_message(chat_id=CHAT_ID, message_id=message_id)
            successful_deletes += 1
            logger.info(f"Сообщение {message_id} удалено")
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения {message_id}: {e}")

    logger.info(f"Удалено {successful_deletes} из {len(last_message_ids)} сообщений")
    last_message_ids = []  # Очищаем список после удаления


async def create_daily_poll():
    """Создает ежедневный опрос с красивым оформлением"""
    global last_message_ids

    try:
        # Удаляем предыдущие сообщения
        await delete_previous_messages()

        # Выбираем случайные варианты для разнообразия
        greeting = random.choice(MORNING_GREETINGS)
        other_option = random.choice(OTHER_OPTIONS)
        description = random.choice(FUNNY_DESCRIPTIONS)

        # Создаем красивый заголовок с эмодзи
        poll_question = f"🦫 ДОБРОЕ УТРО! 🦫\n\n{description}"

        # Отправляем стилизованное сообщение перед опросом
        welcome_message = await application.bot.send_message(
            chat_id=CHAT_ID,
            text=f"🌅 *С БОБРЫМ УТРОМ, ХУЕСОСЫ\!* 🌅\n\n_Пора начинать новый день\!_ ✨\n_Давайте узнаем, как вы сегодня проснулись\!_ 🐾",
            parse_mode='MarkdownV2'
        )
        last_message_ids.append(welcome_message.message_id)

        # Создаем опрос
        poll_message = await application.bot.send_poll(
            chat_id=CHAT_ID,
            question=poll_question,
            options=[greeting, other_option],
            type="regular",
            is_anonymous=False,
            allows_multiple_answers=False
        )
        last_message_ids.append(poll_message.message_id)

        # Добавляем реакцию после создания опроса
        final_message = await application.bot.send_message(
            chat_id=CHAT_ID,
            text="🎉 *Опрос создан\!* \n_Не проголовали = отсосали\!_ 💫",
            parse_mode='MarkdownV2'
        )
        last_message_ids.append(final_message.message_id)

        logger.info(f"Создано {len(last_message_ids)} новых ебаных сообщений")

    except Exception as e:
        logger.error(f"я в ахуе: {e}")


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для тестирования создания опроса"""
    try:
        # Проверяем, находится ли бот в правильном чате
        if str(update.effective_chat.id) != CHAT_ID:
            await update.message.reply_text("❌ Эта команда работает только в указанной группе")
            return

        # Стилизованный ответ
        test_message = await update.message.reply_text(
            "🎪 *я заебался\!* \n_Секундочку\.\.\._ ⏳",
            parse_mode='MarkdownV2'
        )

        await create_daily_poll()

        # Удаляем тестовое сообщение после создания опроса
        try:
            await application.bot.delete_message(chat_id=CHAT_ID, message_id=test_message.message_id)
        except Exception as e:
            logger.error(f"Не удалось удалить тестовое сообщение: {e}")

    except Exception as e:
        logger.error(f"Ошибка в команде /test: {e}")
        await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='MarkdownV2')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ручной очистки сообщений бота"""
    try:
        if str(update.effective_chat.id) != CHAT_ID:
            await update.message.reply_text("❌ Эта команда работает только в указанной группе")
            return

        clear_message = await update.message.reply_text(
            "🧹 ебашу буквы\.\.\.*",
            parse_mode='MarkdownV2'
        )

        await delete_previous_messages()

        await application.bot.edit_message_text(
            chat_id=CHAT_ID,
            message_id=clear_message.message_id,
            text="✅ *выебал буквы\!*",
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        logger.error(f"Ошибка в команде /clear: {e}")
        await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='MarkdownV2')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для показа статистики"""
    try:
        stats_text = f"""
📊 *Статистика бота*

🦫 Бобр работает каждый день в 7:00 по Екатеринбургу
⏰ Следующий опрос: завтра в 7:00
💬 Активных сообщений: {len(last_message_ids)}
🎯 Команды:
   /test \- только коле
   /clear \- уебать по донбассу
   /stats \- нахуя?
   /help \- помощь даунам

*Да прибудет с тобой бобр\!* 🪵
        """
        await update.message.reply_text(stats_text, parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Ошибка в команде /stats: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    try:
        help_text = """
🦫 *Помощь по бобр\-боту*

Этот бот создает ежедневные утренние опросы в 7:00 по Екатеринбургу\.

*Доступные команды:*
`/test` \- создать тестовый опрос \(только для админов\)
`/clear` \- очистить все сообщения бота
`/stats` \- показать статистику бота
`/help` \- эта справка

*Как это работает:*
Каждый день бот автоматически создает новый опрос и удаляет старый\. Просто голосуйте и начинайте день с улыбкой\! 😊

*Примечание:* Бот должен иметь права администратора в группе\.
        """
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Ошибка в команде /help: {e}")


def start_scheduler():
    """Запускает планировщик для ежедневного опроса"""
    try:
        tz = pytz.timezone('Asia/Yekaterinburg')
        scheduler = BackgroundScheduler()

        # Основной опрос в 7:00
        scheduler.add_job(
            create_daily_poll,
            trigger=CronTrigger(hour=7, minute=0, timezone=tz)
        )

        scheduler.start()
        logger.info("🦫 Планировщик запущен! Опросы будут создаваться в 7:00 по Екатеринбургу")
    except Exception as e:
        logger.error(f"Ошибка при запуске планировщика: {e}")


def main():
    """Основная функция"""
    try:
        # Регистрируем команды
        application.add_handler(CommandHandler("test", test_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("start", help_command))

        # Запускаем планировщик
        start_scheduler()

        # Запускаем Flask в отдельном потоке
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Запускаем бота
        logger.info("🦫 Бобр-бот запускается...")
        print("""
    🦫 БОБР-БOT АКТИВИРОВАН! 🦫
    --------------------------
    Статус: Работает
    Функции: Ежедневные опросы в 7:00
    Команды: /test, /clear, /stats, /help
    --------------------------
        """)

        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")


if __name__ == "__main__":
    main()