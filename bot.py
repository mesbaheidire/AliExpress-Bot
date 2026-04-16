import os
import re
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import google.generativeai as genai

# --- 1. كود السيرفر (لإرضاء Render) ---
app = Flask('')
@app.route('/')
def home(): return "Global AliExpress Bot is Live!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

keep_alive()

# --- 2. الإعدادات (تأكد من وضعها في Render Environment Variables) ---
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

MY_SHORT_KEY = "Zx22cv00bnm" # كود الربح الخاص بك
PRICE_BOT_LINK = "https://t.me/Aliprice_bot" # رابط بوت التخفيضات
MY_CHANNEL_ID = "@your_channel_username" # يوزر قناتك (التي سينشر فيها)
SOURCE_CHANNELS = ['@channel1', '@channel2'] # يوزرات القنوات التي ستراقبها

# --- 3. تهيئة المحركات ---
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. منطق تحويل الروابط وإعادة الصياغة ---
@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    if not event.raw_text: return
    
    original_text = event.raw_text
    
    # البحث عن روابط AliExpress واستبدالها برابط الربح الخاص بك
    links = re.findall(r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', original_text)
    modified_text = original_text
    
    for link in links:
        if 'aliexpress' in link:
            affiliate_link = f"https://s.click.aliexpress.com/deep_link.htm?aff_short_key={MY_SHORT_KEY}&dl_target_url={link}"
            modified_text = modified_text.replace(link, affiliate_link)

    # استخدام Gemini لتحويل النص إلى لغة إنجليزية تسويقية احترافية
    prompt = f"""
    Translate and rewrite this product post into professional English marketing style for a global audience.
    Make it catchy with emojis. Keep all links as they are. 
    At the end of the post, add this sentence: "Check price history and coupons here: {PRICE_BOT_LINK}"
    
    Original Post:
    {modified_text}
    """
    
    try:
        response = model.generate_content(prompt)
        final_post = response.text
        
        # النشر في قناتك مع الصورة أو الفيديو الأصلي إن وجد
        await client.send_message(MY_CHANNEL_ID, final_post, file=event.media)
    except Exception as e:
        print(f"Error: {e}")

# --- 5. التشغيل ---
async def main():
    await client.start()
    print("Bot is spying and translating to English...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


   




