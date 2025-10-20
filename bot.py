import os
import subprocess
import requests
import json
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WIT_AI_TOKEN = os.getenv("WIT_AI_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Отправь мне голосовое сообщение — я переведу его в текст!")


def parse_wit_response(raw_text: str):
    """Безопасно разбирает ответ от Wit.ai (когда приходит несколько JSON подряд)."""
    try:
        # Попробуем как обычный JSON
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Пробуем построчно (Wit иногда шлёт много JSON через \n)
    for line in reversed(raw_text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    # Пробуем достать последний {...} через regex
    m = re.search(r'(\{.*\})\s*$', raw_text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    file_path_ogg = "voice.ogg"
    file_path_wav = "voice.wav"

    # Скачиваем голосовое сообщение
    await file.download_to_drive(file_path_ogg)

    # Конвертируем OGG → WAV
    subprocess.run(
        ["ffmpeg", "-y", "-i", file_path_ogg, "-ar", "16000", "-ac", "1", file_path_wav],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Отправляем в Wit.ai
    url = "https://api.wit.ai/speech?v=20220622"
    headers = {
        "Authorization": f"Bearer {WIT_AI_TOKEN}",
        "Content-Type": "audio/wav"
    }

    with open(file_path_wav, "rb") as f:
        response = requests.post(url, headers=headers, data=f)

    raw = response.text
    print("Wit.ai raw response:", raw)  # лог для отладки

    parsed = parse_wit_response(raw)
    if not parsed:
        text = "🤷‍♂️ Не удалось разобрать ответ от Wit.ai."
    else:
        text = parsed.get("text")
        if not text:
            speech = parsed.get("speech", {})
            tokens = speech.get("tokens", [])
            text = " ".join([t.get("token", "").strip() for t in tokens if t.get("token")]) or "🤷‍♂️ Не удалось распознать речь."

        conf = parsed.get("speech", {}).get("confidence")
        if conf is not None:
            text = f"🗣 {text}\n🎯 Уверенность: {round(conf * 100, 1)}%"

    # Удаляем временные файлы
    for path in (file_path_ogg, file_path_wav):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Ошибка при удалении {path}: {e}")

    await update.message.reply_text(text)


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    print("🤖 Bot is starting...")
    app.run_polling()
