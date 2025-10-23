import asyncio
import json
import random
import time
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, ChatWriteForbiddenError, FloodWaitError
from telethon.tl.types import Channel
from telethon.tl.functions.channels import GetFullChannelRequest
import pytz
import os

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
TWO_STEP_PASSWORD = os.getenv('TWO_STEP_PASSWORD', '')

CHANNELS_FILE = "channels.json"
WORDS_FILE = "words.json"

bot_active = False

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_iran_time():
    iran_tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(iran_tz)
    return now.strftime("%H:%M:%S") + f":{now.microsecond // 1000:03d}"

async def send_report(client, report_text):
    await client.send_message('me', report_text)

async def main():
    global bot_active
    
    client = TelegramClient('session_name', API_ID, API_HASH)
    
    await client.start(password=TWO_STEP_PASSWORD)
    
    print("سورس سلف تلگرام آماده است!")
    print("برای مشاهده دستورات، پیام خود را ارسال کنید.")
    
    channels = load_json(CHANNELS_FILE)
    words = load_json(WORDS_FILE)
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^اضافه کردن (.+)$'))
    async def add_channel(event):
        channel_id = event.pattern_match.group(1).strip()
        try:
            channel_id_int = int(channel_id)
            if channel_id_int not in channels:
                channels.append(channel_id_int)
                save_json(CHANNELS_FILE, channels)
                await event.edit(f"✅ کانال {channel_id} با موفقیت اضافه شد")
            else:
                await event.edit(f"⚠️ کانال {channel_id} قبلاً اضافه شده است")
        except ValueError:
            await event.edit("❌ آیدی کانال باید عددی باشد")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^حذف کردن (.+)$'))
    async def remove_channel(event):
        channel_id = event.pattern_match.group(1).strip()
        try:
            channel_id_int = int(channel_id)
            if channel_id_int in channels:
                channels.remove(channel_id_int)
                save_json(CHANNELS_FILE, channels)
                await event.edit(f"✅ کانال {channel_id} با موفقیت حذف شد")
            else:
                await event.edit(f"⚠️ کانال {channel_id} در لیست وجود ندارد")
        except ValueError:
            await event.edit("❌ آیدی کانال باید عددی باشد")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^لیست کانال$'))
    async def list_channels(event):
        if channels:
            channel_list = []
            for ch_id in channels:
                try:
                    ch_entity = await client.get_entity(ch_id)
                    ch_name = ch_entity.title if hasattr(ch_entity, 'title') else str(ch_id)
                    channel_list.append(f"• {ch_name} ({ch_id})")
                except:
                    channel_list.append(f"• {ch_id}")
            await event.edit(f"📋 لیست کانال‌های فعال:\n\n" + "\n".join(channel_list))
        else:
            await event.edit("📋 هیچ کانالی اضافه نشده است")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^تنظیم کلمه (.+)$'))
    async def add_word(event):
        word = event.pattern_match.group(1).strip()
        if word not in words:
            words.append(word)
            save_json(WORDS_FILE, words)
            await event.edit(f"✅ کلمه '{word}' با موفقیت اضافه شد")
        else:
            await event.edit(f"⚠️ کلمه '{word}' قبلاً اضافه شده است")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^حذف کلمه (.+)$'))
    async def remove_word(event):
        word = event.pattern_match.group(1).strip()
        if word in words:
            words.remove(word)
            save_json(WORDS_FILE, words)
            await event.edit(f"✅ کلمه '{word}' با موفقیت حذف شد")
        else:
            await event.edit(f"⚠️ کلمه '{word}' در لیست وجود ندارد")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^لیست کلمات$'))
    async def list_words(event):
        if words:
            word_list = "\n".join([f"• {w}" for w in words])
            await event.edit(f"📋 لیست کلمات:\n\n{word_list}")
        else:
            await event.edit("📋 هیچ کلمه‌ای اضافه نشده است")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^روشن$'))
    async def activate_bot(event):
        global bot_active
        bot_active = True
        await event.edit("✅ ربات روشن شد\nحالت کامنت‌گذاری فعال است")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^خاموش$'))
    async def deactivate_bot(event):
        global bot_active
        bot_active = False
        await event.edit("❌ ربات خاموش شد\nحالت کامنت‌گذاری غیرفعال است")
    
    @client.on(events.NewMessage(outgoing=True, pattern=r'^پینگ$'))
    async def ping(event):
        start_time = time.time()
        await asyncio.sleep(0.001)
        end_time = time.time()
        ping_ms = round((end_time - start_time) * 1000, 2)
        status = "روشن ✅" if bot_active else "خاموش ❌"
        await event.edit(f"🏓 پینگ: {ping_ms} میلی‌ثانیه\n📊 وضعیت: {status}")
    
    @client.on(events.NewMessage(chats=channels))
    async def handle_new_post(event):
        if not bot_active:
            return
        
        if not words:
            return
        
        channel_id = event.chat_id
        post_time = get_iran_time()
        
        try:
            channel = await client.get_entity(channel_id)
            channel_name = channel.title if hasattr(channel, 'title') else str(channel_id)
            
            discussion_group_id = None
            try:
                if isinstance(channel, Channel):
                    full_channel = await client(GetFullChannelRequest(channel))
                    if hasattr(full_channel.full_chat, 'linked_chat_id') and full_channel.full_chat.linked_chat_id:
                        discussion_group_id = full_channel.full_chat.linked_chat_id
            except:
                pass
            
            if not discussion_group_id:
                report = f"⚠️ گزارش ناموفق\n\n"
                report += f"📢 کانال: {channel_name}\n"
                report += f"🔗 لینک پست: https://t.me/c/{str(channel_id)[4:]}/{event.message.id}\n"
                report += f"⏰ زمان پست: {post_time}\n"
                report += f"❌ وضعیت: ناموفق - گروه لینک شده یافت نشد"
                await send_report(client, report)
                return
            
            selected_word = random.choice(words)
            
            attempt_count = 0
            max_attempts = 50
            comment_sent = False
            comment_link = None
            comment_time = None
            
            last_error = None
            while attempt_count < max_attempts and not comment_sent:
                attempt_count += 1
                try:
                    if attempt_count == 1:
                        await asyncio.sleep(0.05)
                    else:
                        await asyncio.sleep(0.3)
                    
                    comment_msg = await client.send_message(
                        channel,
                        selected_word,
                        comment_to=event.message.id
                    )
                    
                    comment_sent = True
                    comment_time = get_iran_time()
                    comment_link = f"https://t.me/c/{str(discussion_group_id)[4:]}/{comment_msg.id}"
                    
                except ChatWriteForbiddenError as e:
                    last_error = f"گروه بسته است: {str(e)}"
                    await asyncio.sleep(1.5)
                    continue
                    
                except FloodWaitError as e:
                    last_error = f"محدودیت سرعت: {e.seconds} ثانیه صبر"
                    await asyncio.sleep(e.seconds)
                    continue
                    
                except Exception as e:
                    last_error = f"{type(e).__name__}: {str(e)}"
                    print(f"خطا در تلاش {attempt_count} برای {channel_name}: {last_error}")
                    await asyncio.sleep(0.8)
                    continue
            
            if comment_sent:
                report = f"✅ گزارش موفق\n\n"
                report += f"📢 کانال: {channel_name}\n"
                report += f"🔗 لینک پست: https://t.me/c/{str(channel_id)[4:]}/{event.message.id}\n"
                report += f"⏰ زمان پست: {post_time}\n"
                report += f"⏰ زمان کامنت: {comment_time}\n"
                report += f"💬 لینک کامنت: {comment_link}\n"
                report += f"🔄 تعداد تلاش: {attempt_count}\n"
                report += f"✅ وضعیت: موفق"
            else:
                report = f"⚠️ گزارش ناموفق\n\n"
                report += f"📢 کانال: {channel_name}\n"
                report += f"🔗 لینک پست: https://t.me/c/{str(channel_id)[4:]}/{event.message.id}\n"
                report += f"⏰ زمان پست: {post_time}\n"
                report += f"🔄 تعداد تلاش: {attempt_count}\n"
                if last_error:
                    report += f"⚠️ آخرین خطا: {last_error}\n"
                report += f"❌ وضعیت: ناموفق"
            
            await send_report(client, report)
            
        except Exception as e:
            report = f"❌ خطا در پردازش\n\n"
            report += f"📢 کانال: {channel_id}\n"
            report += f"⏰ زمان: {post_time}\n"
            report += f"⚠️ خطا: {str(e)}"
            await send_report(client, report)
    
    print("✅ ربات در حال اجراست...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
