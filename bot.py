import os
import sys
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler

ENV_FILE = ".env"

def load_or_create_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except ImportError:
        pass

    api_token = os.getenv("API_TOKEN")
    chat_id_env = os.getenv("CHAT_ID")
    poll_time = os.getenv("POLL_TIME", "12:00")       # Время запуска опроса
    poll_duration = os.getenv("POLL_DURATION", "60")   # Продолжительность в минутах

    updated = False
    if not api_token:
        api_token = input("👉 Введи API_TOKEN: ").strip()
        updated = True

    if not chat_id_env:
        chat_id_env = input("👉 Введи CHAT_ID: ").strip()
        updated = True

    if updated:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"API_TOKEN={api_token}\n")
            f.write(f"CHAT_ID={chat_id_env}\n")
            f.write(f"POLL_TIME={poll_time}\n")
            f.write(f"POLL_DURATION={poll_duration}\n")
        print(f"✅ Файл {ENV_FILE} создан/обновлён")

    try:
        chat_id_int = int(chat_id_env)
    except ValueError:
        print("❌ CHAT_ID должен быть числом")
        sys.exit(1)

    try:
        poll_duration_int = int(poll_duration)
    except ValueError:
        print("❌ POLL_DURATION должен быть числом минут")
        sys.exit(1)

    return api_token, chat_id_int, poll_time, poll_duration_int

API_TOKEN, CHAT_ID, POLL_TIME, POLL_DURATION = load_or_create_env()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словарь для подсчета голосов
poll_votes = {}  # {poll_id: {"plus": 0, "minus": 0}}

async def send_poll():
    """Создаёт опрос и запускает таймер для отчёта"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m")
    question = f"Ланч на {tomorrow}?"
    options = ["+", "-"]

    poll_msg = await bot.send_poll(
        chat_id=CHAT_ID,
        question=question,
        options=options,
        is_anonymous=False,
        open_period=POLL_DURATION*60  # В секундах
    )

    # Инициализируем словарь для подсчета голосов
    poll_votes[poll_msg.poll.id] = {"plus": 0, "minus": 0}

    print(f"📢 Опрос отправлен: {question} | Длительность: {POLL_DURATION} мин | Время: {datetime.now().strftime('%H:%M:%S')}")

    # Ждём окончания опроса
    await asyncio.sleep(POLL_DURATION*60)

    # Формируем отчёт и отправляем в чат
    votes = poll_votes.pop(poll_msg.poll.id, {"plus": 0})
    plus_count = votes["plus"]

    report = (
        "Сборочное производство\n"
        f"Ланч на {tomorrow}\n"
        f"{plus_count} шт"
    )

    await bot.send_message(CHAT_ID, report)
    print(f"📊 Отчёт отправлен в чат | +: {plus_count} шт | Время: {datetime.now().strftime('%H:%M:%S')}")

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer):
    """Сохраняем ответы пользователей"""
    poll_id = poll_answer.poll_id
    if poll_id not in poll_votes:
        return

    plus_count = 0
    minus_count = 0
    for idx in poll_answer.option_ids:
        if idx == 0:
            plus_count += 1
        elif idx == 1:
            minus_count += 1

    poll_votes[poll_id]["plus"] = plus_count
    poll_votes[poll_id]["minus"] = minus_count

async def scheduler():
    """Планировщик для ежедневного запуска опроса"""
    scheduler = AsyncIOScheduler(timezone="Europe/Kiev")
    try:
        hour, minute = map(int, POLL_TIME.split(":"))
    except ValueError:
        print("❌ POLL_TIME должен быть в формате HH:MM")
        sys.exit(1)

    scheduler.add_job(send_poll, "cron", hour=hour, minute=minute)
    scheduler.start()

    print(f"🟢 Бот запущен! Текущее время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"⏰ Ежедневный опрос будет отправляться в {hour:02d}:{minute:02d} и длиться {POLL_DURATION} мин")

async def main():
    await scheduler()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
