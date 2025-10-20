import os
import subprocess
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8320004321:AAGWzpqHz16JI0NIepkg0SDPPgnDi29Q9lQ"
WIT_AI_TOKEN = "S5SW7YEVF76FX5T2GGZWEY7O7KFJHIC6"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Отправь мне голосовое сообщение — я переведу его в текст!")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    file_path_ogg = "voice.ogg"
    file_path_wav = "voice.wav"

    # Скачиваем голосовое сообщение
    await file.download_to_drive(file_path_ogg)

    # Конвертируем OGG → WAV
    subprocess.run(["ffmpeg", "-y", "-i", file_path_ogg, "-ar", "16000", file_path_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Отправляем в Wit.ai
    url = "https://api.wit.ai/speech?v=20220622"
    headers = {
        "Authorization": f"Bearer {WIT_AI_TOKEN}",
        "Content-Type": "audio/wav"
    }

    with open(file_path_wav, "rb") as f:
        response = requests.post(url, headers=headers, data=f)

    # Логируем ответ, чтобы отладить при необходимости
    print("Wit.ai raw response:", response.text)

    try:
        data = response.json()
        text = data.get("text", "🤷‍♂️ Не удалось распознать речь.")
    except Exception as e:
        text = f"Произошла ошибка: {e}"

    await update.message.reply_text(text)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    print("🤖 Bot is starting...")
    app.run_polling()
