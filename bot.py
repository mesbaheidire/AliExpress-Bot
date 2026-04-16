import os
import subprocess
import sys

# أمر إجباري لتثبيت المكتبة إذا لم يجدها السيرفر
try:
    import google.generativeai as genai
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-generativeai"])
    import google.generativeai as genai

import re
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# --- بقية الكود كما هو ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

keep_alive()

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
GEMINI_KEY = os.environ.get('GEMINI_KEY')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

MY_SHORT_KEY = "Zx22cv00bnm"
PRICE_BOT_LINK = "https://t.me/Aliprice_bot"
SOURCE_CHANNELS = ['me'] 

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    if not event.raw_text: return
    text = event.raw_text
    links = re.findall(r'https?://[^\s]+aliexpress[^\s]+', text)
    for link in links:
        aff_link = f"https://s.click.aliexpress.com/deep_link.htm?aff_short_key={MY_SHORT_KEY}&dl_target_url={link}"
        text = text.replace(link, aff_link)
    
    prompt = f"Rewrite this in English for marketing: {text} \n\nCheck price: {PRICE_BOT_LINK}"
    response = model.generate_content(prompt)
    await client.send_message(CHANNEL_ID, response.text, file=event.media)

async def main():
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


