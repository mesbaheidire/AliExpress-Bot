import re
import os
import asyncio
import signal
from google import genai
from telethon import TelegramClient, events
from telethon.tl.types import Channel, MessageMediaPhoto, MessageMediaDocument

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

# Matches any AliExpress link variant:
# aliexpress.com, m.aliexpress.com, s.click.aliexpress.com,
# aliexpress.ru, a.aliexpress.com, shortlinks, etc.
ALIEXPRESS_RE = re.compile(
    r'https?://[^\s<>"\']*aliexpress[^\s<>"\']*',
    re.IGNORECASE
)


def get_real_media(message):
    """Return media only if it's a real file (photo/video/doc), not a web preview."""
    media = message.media
    if isinstance(media, (MessageMediaPhoto, MessageMediaDocument)):
        return media
    return None


def make_affiliate_link(original_url: str) -> str:
    """Convert any AliExpress URL to an affiliate deep link."""
    base_url = "https://s.click.aliexpress.com/deep_link.htm"
    clean_url = original_url.split('?')[0]
    return f"{base_url}?aff_short_key={MY_SHORT_KEY}&dl_target_url={clean_url}"


def replace_affiliate_links(text: str) -> tuple[str, list[str]]:
    """Find all AliExpress URLs in text and replace with affiliate links."""
    urls = ALIEXPRESS_RE.findall(text)
    if not urls:
        return text, []
    processed = text
    for url in urls:
        processed = processed.replace(url, make_affiliate_link(url))
    return processed, urls


async def rewrite_to_english_marketing(text: str) -> str:
    """Use Gemini to rewrite deal text as catchy English marketing copy."""
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


# Single handler — no incoming/outgoing filter so we catch everything
@client.on(events.NewMessage())
async def router(event):
    global MY_USER_ID
    if MY_USER_ID is None:
        return

    # ── Route A: Saved Messages (forward/direct message from the user to themselves) ──
    if event.chat_id == MY_USER_ID:
        await handle_saved_messages(event)
        return

    # ── Route B: Auto-spy on subscribed broadcast channels ──
    if event.is_channel:
        chat = await event.get_chat()
        if isinstance(chat, Channel) and getattr(chat, 'broadcast', False):
            await handle_channel_post(event, chat)


async def handle_saved_messages(event):
    """Process a message forwarded or sent to Saved Messages."""
    text = event.message.text or ""

    # Also scan caption on media messages (images with text)
    if not text and event.message.media:
        text = getattr(event.message, 'message', "") or ""

    processed_text, urls = replace_affiliate_links(text)

    if not urls:
        await client.send_message(
            MY_USER_ID,
            "⚠️ No AliExpress links found in this message.\n"
            "Please forward a post that contains an AliExpress product link."
        )
        return

    final_text = processed_text + ARABIC_FOOTER

    print(f"📋 Manual forward received — {len(urls)} link(s) converted, sending preview...")

    try:
        await client.send_message(
            MY_USER_ID,
            f"✅ *Your modified post — ready to review:*\n\n"
            f"─────────────────\n"
            f"{final_text}\n"
            f"─────────────────\n\n"
            f"👆 Copy the text above and post it when ready.",
            file=get_real_media(event.message),
            link_preview=True,
            parse_mode='md'
        )
        print("✅ Manual preview sent to user.")
    except Exception as e:
        print(f"❌ Error sending manual preview: {e}")


async def handle_channel_post(event, chat):
    """Auto-process a deal from a monitored broadcast channel."""
    if not event.message.text:
        return

    processed_text, urls = replace_affiliate_links(event.message.text)
    if not urls:
        return

    channel_title = getattr(chat, 'title', str(event.chat_id))
    print(f"🔗 Found deal in '{channel_title}' — {len(urls)} link(s), rewriting...")

    final_english_post = await rewrite_to_english_marketing(processed_text)

    try:
        await client.send_message(
            MY_CHANNEL,
            final_english_post,
            file=get_real_media(event.message),
            link_preview=True
        )
        print(f"✅ Auto-posted to {MY_CHANNEL} from '{channel_title}'")
    except Exception as e:
        print(f"❌ Error sending message: {e}")


async def main():
    global MY_USER_ID
    await client.start()
    me = await client.get_me()
    MY_USER_ID = me.id
    print(f"✅ Logged in as: {me.first_name} (@{me.username}) — ID: {MY_USER_ID}")
    print(f"📡 Auto-monitoring all subscribed broadcast channels for AliExpress deals")
    print(f"📢 Auto-posting to: {MY_CHANNEL}")
    print(f"📋 Manual mode: forward any post to your Saved Messages to get a preview")
    await client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot stopped gracefully.")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        raise
