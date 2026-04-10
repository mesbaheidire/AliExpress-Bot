import re
import os
import asyncio
from google import genai
from telethon import TelegramClient, events
from telethon.tl.types import Channel

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

MY_SHORT_KEY = "Zx22cv00bnm"
MY_CHANNEL = '@asdfgh051'

gemini_client = genai.Client(api_key=GEMINI_KEY)

client = TelegramClient('user_session', API_ID, API_HASH)


def make_affiliate_link(original_url: str) -> str:
    base_url = "https://s.click.aliexpress.com/deep_link.htm"
    clean_url = original_url.split('?')[0]
    return f"{base_url}?aff_short_key={MY_SHORT_KEY}&dl_target_url={clean_url}"


async def rewrite_to_english_marketing(text: str) -> str:
    prompt = f"""Context: You are a professional English affiliate marketer for AliExpress deals.
Task: Rewrite the following deal description into high-converting, professional, and catchy ENGLISH for a Telegram audience.
Guidelines:
- Use attractive shopping emojis.
- Highlight the product benefits and the deal.
- Make the call to action clear.
- KEEP the links exactly as provided in the processed text.
- Ensure the final output is ONLY in English.

Original Message:
{text}"""
    try:
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini AI Error: {e}")
        return text


@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.message.text:
        return

    chat = await event.get_chat()

    if not isinstance(chat, Channel):
        return

    if not getattr(chat, 'broadcast', False):
        return

    original_text = event.message.text

    urls = re.findall(
        r'(https?://(?:[^\s]*aliexpress\.com|[^\s]*s\.click\.aliexpress\.com)[^\s]*)',
        original_text
    )

    if not urls:
        return

    processed_text = original_text
    for url in urls:
        my_aff_link = make_affiliate_link(url)
        processed_text = processed_text.replace(url, my_aff_link)

    print(f"🔗 Found deal in '{getattr(chat, 'title', event.chat_id)}', rewriting...")
    final_english_post = await rewrite_to_english_marketing(processed_text)

    try:
        await client.send_message(
            MY_CHANNEL,
            final_english_post,
            file=event.message.media,
            link_preview=True
        )
        print(f"✅ Posted to {MY_CHANNEL} successfully!")
    except Exception as e:
        print(f"❌ Error sending message: {e}")


async def main():
    await client.start()
    me = await client.get_me()
    print(f"✅ Logged in as: {me.first_name} (@{me.username})")
    print(f"📡 Monitoring ALL subscribed broadcast channels for AliExpress deals...")
    print(f"📢 Posting deals to: {MY_CHANNEL}")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
