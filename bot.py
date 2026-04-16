import os
import re
import asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import google.generativeai as genai

# --- 1. إعداد السيرفر (Render Web Service) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online and Spying..."

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

keep_alive()

# --- 2. جلب البيانات من بيئة Render ---
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
GEMINI_KEY = os.environ.get('GEMINI_KEY')
CHANNEL_ID = os.environ.get('CHANNEL_ID') # يوزر قناتك يبدأ بـ @

# إعداداتك الخاصة
MY_SHORT_KEY = "Zx22cv00bnm"
PRICE_BOT_LINK = "https://t.me/Aliprice_bot"
# أضف يوزرات القنوات هنا، وكلمة 'me' تعني رسائلك المحفوظة
SOURCE_CHANNELS = ['me', '@example_channel'] 

# --- 3. تهيئة المحركات ---
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 4. منطق معالجة الرسائل ---
@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    if not event.raw_text: return
    
    original_text = event.raw_text
    # استخراج روابط AliExpress
    links = re.findall(r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', original_text)
    
    modified_text = original_text
    has_aliexpress = False
    
    for link in links:
        if 'aliexpress' in link:
            has_aliexpress = True
            # تحويل الرابط لرابط ربحي
            affiliate_link = f"https://s.click.aliexpress.com/deep_link.htm?aff_short_key={MY_SHORT_KEY}&dl_target_url={link}"
            modified_text = modified_text.replace(link, affiliate_link)

    if has_aliexpress:
        # استخدام Gemini للترجمة وإعادة الصياغة للإنجليزية
        prompt = f"Rewrite this AliExpress product post in professional English marketing style with emojis. Keep the links as they are. End with: 'Check price history here: {PRICE_BOT_LINK}' \n\nContent: {modified_text}"
        
        try:
            response = model.generate_content(prompt)
            final_post = response.text
            # النشر في قناتك
            await client.send_message(CHANNEL_ID, final_post, file=event.media)
        except Exception as e:
            print(f"Error with Gemini: {e}")

# --- 5. التشغيل ---
async def main():
    await client.start()
    print("Bot is Started Successfully!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
   




