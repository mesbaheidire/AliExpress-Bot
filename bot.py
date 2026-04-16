import os
import re
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events
import google.generativeai as genai

# --- الإعدادات (تأكد من وجودها في Render Environment Variables) ---
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
CHANNEL_ID = os.environ.get('CHANNEL_ID') # يجب أن يكون @ahmde500
MY_SHORT_KEY = os.environ.get('MY_SHORT_KEY')

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# إعداد Telegram Client
client = TelegramClient(SESSION_STRING, API_ID, API_HASH)

# --- خادم الويب (لمنع خطأ 502 وإرضاء Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Alive and Running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- معالج الرسائل الذكي ---
@client.on(events.NewMessage)
async def handler(event):
    # مراقبة أي رسالة تحتوي على aliexpress
    if event.raw_text and 'aliexpress' in event.raw_text.lower():
        print(f"📩 اكتشفت رابطاً من: {event.chat_id}")
        
        # استخراج الرابط
        links = re.findall(r'https?://[^\s]+', event.raw_text)
        if not links: return
        original_link = links[0]
        
        # إنشاء الرابط الربحي
        aff_link = f"https://s.click.aliexpress.com/deep_link.htm?aff_short_key={MY_SHORT_KEY}&dl_target_url={original_link}"
        
        try:
            # طلب الصياغة من Gemini
            prompt = f"Create a short, catchy English marketing post for this product: {original_link}. Add emojis and call to action."
            response = model.generate_content(prompt)
            final_text = f"{response.text}\n\n🛒 Order Here: {aff_link}"
            
            # النشر في القناة (مع التأكد من وجود ميديا أو لا)
            if event.media:
                await client.send_message(CHANNEL_ID, final_text, file=event.media)
            else:
                await client.send_message(CHANNEL_ID, final_text)
            
            print("🚀 تم النشر في القناة!")
        except Exception as e:
            print(f"❌ خطأ أثناء المعالجة: {e}")

# --- تشغيل البوت ---
async def main():
    await client.start()
    # رسالة ترحيب لتتأكد أن الربط نجح
    await client.send_message('me', "✅ البوت متصل الآن بحسابك وجاهز للعمل!")
    print("✅ Telegram Client Started!")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # تشغيل Flask في خيط منفصل
    Thread(target=run_flask).start()
    
    # تشغيل تليجرام
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


