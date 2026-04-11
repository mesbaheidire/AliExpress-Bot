import re
import os
import asyncio
from google import genai
from telethon import TelegramClient, events
from telethon.tl.types import Channel, User

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
GEMINI_KEY = os.environ.get('GEMINI_KEY')

MY_SHORT_KEY = "Zx22cv00bnm"
MY_CHANNEL = '@asdfgh051'
PRICE_BOT_LINK = "https://t.me/Aliprice_bot"
ARABIC_FOOTER = f"\n\n🏷️ للحصول على تخفيض إضافي استخدم بوت التخفيضات:\n{PRICE_BOT_LINK}"

gemini_client = genai.Client(api_key=GEMINI_KEY)

client = TelegramClient('user_session', API_ID, API_HASH)

MY_USER_ID = None


def make_affiliate_link(original_url: str) -> str:
    base_url = "https://s.click.aliexpress.com/deep_link.htm"
    clean_url = original_url.split('?')[0]
    return f"{base_url}?aff_short_key={MY_SHORT_KEY}&dl_target_url={clean_url}"


def replace_affiliate_links(text: str) -> tuple[str, list]:
    urls = re.findall(
        r'(https?://(?:[^\s]*aliexpress\.com|[^\s]*s\.click\.aliexpress\.com)[^\s]*)',
        text
    )
    if not urls:
        return text, []
    processed = text
    for url in urls:
        processed = processed.replace(url, make_affiliate_link(url))
    return processed, urls


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


# --- Handler 1: Auto-spy on subscribed broadcast channels ---
@client.on(events.NewMessage(incoming=True))
async def channel_spy_handler(event):
    if not event.message.text:
        return

    chat = await event.get_chat()

    if not isinstance(chat, Channel):
        return
    if not getattr(chat, 'broadcast', False):
        return

    processed_text, urls = replace_affiliate_links(event.message.text)
    if not urls:
        return

    print(f"🔗 Found deal in '{getattr(chat, 'title', event.chat_id)}', rewriting...")
    final_english_post = await rewrite_to_english_marketing(processed_text)

    try:
        await client.send_message(
            MY_CHANNEL,
            final_english_post,
            file=event.message.media,
            link_preview=True
        )
        print(f"✅ Auto-posted to {MY_CHANNEL} successfully!")
    except Exception as e:
        print(f"❌ Error sending message: {e}")


# --- Handler 2: Manual Forward — user forwards a post directly to themselves (Saved Messages) ---
@client.on(events.NewMessage(incoming=True))
async def manual_forward_handler(event):
    global MY_USER_ID
    if MY_USER_ID is None:
        return

    # Only handle messages in the user's own Saved Messages (chat with themselves)
    if event.chat_id != MY_USER_ID:
        return

    if not event.message.text and not event.message.media:
        return

    text = event.message.text or ""

    processed_text, urls = replace_affiliate_links(text)
    if not urls:
        # No AliExpress links found — let user know
        await client.send_message(
            MY_USER_ID,
            "⚠️ No AliExpress links found in the forwarded message. Please forward a post that contains an AliExpress product link."
        )
        return

    # Append Arabic footer
    final_text = processed_text + ARABIC_FOOTER

    print(f"📋 Manual forward received — sending preview back to user...")
    try:
        await client.send_message(
            MY_USER_ID,
            f"✅ Here is your modified post for review:\n\n─────────────────\n{final_text}\n─────────────────\n\n👆 Copy the text above and post it when ready.",
            file=event.message.media,
            link_preview=True
        )
        print("✅ Manual preview sent to user.")
    except Exception as e:
        print(f"❌ Error sending manual preview: {e}")


async def main():
    global MY_USER_ID
    await client.start()
    me = await client.get_me()
    MY_USER_ID = me.id
    print(f"✅ Logged in as: {me.first_name} (@{me.username}) — ID: {MY_USER_ID}")
    print(f"📡 Monitoring ALL subscribed broadcast channels for AliExpress deals...")
    print(f"📢 Auto-posting deals to: {MY_CHANNEL}")
    print(f"📋 Manual Forward: forward any post to your Saved Messages to preview it with affiliate links + footer.")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
