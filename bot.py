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
    # حل مشكلة الـ Event Loop في السيرفرات
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    print(f"🔄 تم اكتشاف رسالة جديدة من: {event.chat_id}")
    
    if not event.raw_text:
        print("❌ الرسالة فارغة")
        return
    
    # البحث عن روابط علي اكسبريس
    links = re.findall(r'https?://[^\s]+aliexpress[^\s]+', event.raw_text)
    
    if not links:
        print("ℹ️ الرسالة لا تحتوي على روابط AliExpress")
        return

    print(f"🔗 تم العثور على {len(links)} رابط، جاري المعالجة...")
    # ... بقية الكود الخاص بـ Gemini والنشر
# اجعل البوت يراقب كل شيء بدون تحديد 'me' مؤقتاً للتأكد من العمل
@client.on(events.NewMessage) 
async def handler(event):
    # طباعة في السجلات لنتأكد أن البوت استلم شيئاً
    print(f"📩 وصلت رسالة جديدة: {event.raw_text}")

    if event.raw_text and 'aliexpress' in event.raw_text.lower():
        print("✅ تم العثور على رابط AliExpress!")
        
        # استخراج الرابط من النص
        links = re.findall(r'https?://[^\s]+', event.raw_text)
        if not links: return
        link = links[0]
        
        # تحويل الرابط لرابطك الربحي
        aff_link = f"https://s.click.aliexpress.com/deep_link.htm?aff_short_key={MY_SHORT_KEY}&dl_target_url={link}"
        
        # صياغة المنشور عبر Gemini
        try:
            prompt = f"Write a catchy English marketing post for this product: {link}. Include emojis."
            response = model.generate_content(prompt)
            final_text = f"{response.text}\n\n🛒 Buy here: {aff_link}"
            
            # النشر في القناة
            await client.send_message(CHANNEL_ID, final_text, file=event.media)
            print("🚀 تم النشر في القناة بنجاح!")
        except Exception as e:
            print(f"❌ خطأ أثناء النشر: {e}")
async def main():
    await client.start()
    # هذه الرسالة ستُرسل لك فور تشغيل البوت لتتأكد أنه اتصل بحسابك
    await client.send_message('me', "✅ أنا أعمل الآن وأراقب روابط AliExpress!")
    print("Bot is Started Successfully!")
    await client.run_until_disconnected()
