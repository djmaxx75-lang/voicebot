import tempfile
import subprocess
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WIT_AI_TOKEN = os.getenv("WIT_AI_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply("🎤 Отправь мне голосовое сообщение — я переведу его в текст!")

@dp.message_handler(content_types=['voice'])
async def voice_to_text(message: types.Message):
    try:
        file = await bot.get_file(message.voice.file_id)
        ogg_file = tempfile.mktemp(suffix=".ogg")
        wav_file = ogg_file.replace(".ogg", ".wav")
        await bot.download_file(file.file_path, ogg_file)

        subprocess.run(['ffmpeg', '-i', ogg_file, '-ar', '16000', '-ac', '1', wav_file, '-y'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        headers = {'Authorization': f'Bearer {WIT_AI_TOKEN}', 'Content-Type': 'audio/wav'}
        with open(wav_file, 'rb') as audio:
            response = requests.post('https://api.wit.ai/speech?v=20210928',
                                     headers=headers, data=audio)

        if response.status_code == 200:
            text = response.json().get('text', '').strip()
            if text:
                await message.reply(f"🗣 {text}")
            else:
                await message.reply("Не удалось распознать речь 😕")
        else:
            await message.reply(f"Ошибка: {response.status_code}")

    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

    finally:
        for f in [ogg_file, wav_file]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    executor.start_polling(dp)
