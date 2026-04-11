import re
import os
import asyncio
import signal
from google import genai
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Channel, MessageMediaPhoto, MessageMediaDocument

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
GEMINI_KEY = os.environ.get('GEMINI_KEY')
SESSION_STRING = os.environ.get('SESSION_STRING', '')

MY_SHORT_KEY = "Zx22cv00bnm"
MY_CHANNEL = '@asdfgh051'
PRICE_BOT_LINK = "https://t.me/Aliprice_bot"
ENGLISH_FOOTER = (
    f"\n\n💡 Don't forget to use the bot to get the best offers and discounts "
    f"for various AliExpress products!\n🤖 {PRICE_BOT_LINK}"
    f"\n\n#AliExpress #Deals #Shopping #Discounts #AliExpressDeals"
)

gemini_client = genai.Client(api_key=GEMINI_KEY)

# Use StringSession if SESSION_STRING env var is set (e.g. on Render),
# otherwise fall back to the local session file (Replit dev environment).
_session = StringSession(SESSION_STRING) if SESSION_STRING else 'user_session'
client = TelegramClient(_session, API_ID, API_HASH)

MY_USER_ID = None

# ── Regex patterns ──────────────────────────────────────────────────────────

ALIEXPRESS_RE = re.compile(
    r'https?://[^\s<>"\']*aliexpress[^\s<>"\']*',
    re.IGNORECASE
)

# All Arabic Unicode blocks:
# 0600-06FF  Arabic core
# 0750-077F  Arabic Supplement
# 08A0-08FF  Arabic Extended-A
# FB50-FDFF  Arabic Presentation Forms-A
# FE70-FEFF  Arabic Presentation Forms-B
ARABIC_RE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+'
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def has_arabic(text: str) -> bool:
    """Return True if the text contains any Arabic characters."""
    return bool(ARABIC_RE.search(text))


def clean_text(text: str) -> str:
    """
    Hard-remove every Arabic character from the text.
    URLs are never touched (they never contain Arabic).
    Cleans up leftover double-spaces/newlines afterwards.
    """
    cleaned = ARABIC_RE.sub('', text)
    # Collapse multiple blank lines left after stripping
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r'  +', ' ', cleaned)
    return cleaned.strip()


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


# ── Gemini rewrite ───────────────────────────────────────────────────────────

async def rewrite_to_english_marketing(text: str) -> str:
    """
    Use Gemini to produce 100% English marketing copy.
    Afterwards, strip_arabic is applied as a hard safety net.
    """
    prompt = f"""You are a professional English affiliate marketer for AliExpress deals.

Task: Rewrite the message below into high-converting, catchy ENGLISH for a Telegram shopping channel.

Rules — follow every one strictly:
1. The output MUST be 100% English. Zero Arabic, Chinese, or any other non-English language — not even a single character.
2. If the original message is in Arabic or any other language, translate it fully into English first, then rewrite it.
3. Use attractive shopping emojis throughout.
4. Highlight the product name, key benefits, and the deal/discount clearly.
5. End with a strong English call to action (e.g. "Grab yours now! ⚡", "Limited time deal! 🔥").
6. KEEP every URL exactly as it appears — do not modify, shorten, or remove any link.
7. Do NOT add hashtags — they are added separately.

Original Message:
{text}"""
    try:
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        result = response.text
    except Exception as e:
        print(f"Gemini AI Error: {e}")
        result = text

    # Hard safety net — strip any Arabic that slipped through
    if has_arabic(result):
        print("⚠️ Arabic detected in Gemini output — stripping...")
        result = clean_text(result)

    return result


# ── Router ───────────────────────────────────────────────────────────────────

@client.on(events.NewMessage())
async def router(event):
    global MY_USER_ID
    if MY_USER_ID is None:
        return

    # Route A: Saved Messages — manual forward
    if event.chat_id == MY_USER_ID:
        await handle_saved_messages(event)
        return

    # Route B: Auto-spy broadcast channels
    if event.is_channel:
        chat = await event.get_chat()
        if isinstance(chat, Channel) and getattr(chat, 'broadcast', False):
            await handle_channel_post(event, chat)


# ── Saved Messages handler ────────────────────────────────────────────────────

async def handle_saved_messages(event):
    """
    Process a manual forward in Saved Messages.
    Always runs through Gemini (translates Arabic if present),
    then posts the clean English result directly to the channel.
    """
    text = event.message.text or getattr(event.message, 'message', '') or ''

    processed_text, urls = replace_affiliate_links(text)

    if not urls:
        print("⚠️ Manual forward — no AliExpress links found, skipping.")
        return

    print(f"📋 Manual forward — {len(urls)} link(s), rewriting via Gemini...")
    final_text = await rewrite_to_english_marketing(processed_text)

    # Extra safety: strip any remaining Arabic before posting
    if has_arabic(final_text):
        final_text = clean_text(final_text)

    try:
        await client.send_message(
            MY_CHANNEL,
            final_text + ENGLISH_FOOTER,
            file=get_real_media(event.message),
            link_preview=True
        )
        print(f"✅ Manual forward posted to {MY_CHANNEL}!")
    except Exception as e:
        print(f"❌ Error posting manual forward: {e}")


# ── Channel auto-spy handler ─────────────────────────────────────────────────

async def handle_channel_post(event, chat):
    """Auto-process a deal from a monitored broadcast channel."""
    if not event.message.text:
        return

    processed_text, urls = replace_affiliate_links(event.message.text)
    if not urls:
        return

    channel_title = getattr(chat, 'title', str(event.chat_id))
    print(f"🔗 Found deal in '{channel_title}' — {len(urls)} link(s), rewriting...")

    final_text = await rewrite_to_english_marketing(processed_text)

    # Extra safety: strip any remaining Arabic before posting
    if has_arabic(final_text):
        final_text = clean_text(final_text)

    try:
        await client.send_message(
            MY_CHANNEL,
            final_text + ENGLISH_FOOTER,
            file=get_real_media(event.message),
            link_preview=True
        )
        print(f"✅ Auto-posted to {MY_CHANNEL} from '{channel_title}'")
    except Exception as e:
        print(f"❌ Error sending message: {e}")


# ── Startup & reconnect loop ─────────────────────────────────────────────────

_stop = False


def _handle_sigterm(*_):
    global _stop
    _stop = True
    print("🛑 SIGTERM received — shutting down...")


async def main():
    global MY_USER_ID, _stop

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    await client.start()
    print(f"MY_SESSION_STR: {client.session.save()}")
    me = await client.get_me()
    MY_USER_ID = me.id
    print(f"✅ Logged in as: {me.first_name} (@{me.username}) — ID: {MY_USER_ID}")
    print(f"📡 Auto-monitoring all subscribed broadcast channels for AliExpress deals")
    print(f"📢 Auto-posting to: {MY_CHANNEL}")
    print(f"📋 Manual mode: forward any post to your Saved Messages to trigger posting")

    RECONNECT_DELAY = 10

    while not _stop:
        try:
            if not client.is_connected():
                print("🔄 Reconnecting to Telegram...")
                await client.connect()
            await client.run_until_disconnected()
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            if _stop:
                break
            print(f"⚠️ Connection lost: {e} — retrying in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)

    await client.disconnect()
    print("🛑 Bot stopped gracefully.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        raise
