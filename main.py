from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import re

# ========== CONFIG ==========
STRING_SESSION = '1BVtsOHgBuwz81Gpdu_OrzLFbEan8_QF2iP5EWy5K8iPkHz1lFWooNpcYum30kSi1JnDGbFgksHxm4Qeopxo7WyL6Ap-JigFe7K2iusTJmC_vK73YArSBdKUlKYeW6S_npL5OVjmyvkPAFX43WsTBrIMCgEG2FUMwUtnLR7KgOG2iRNmdphxabQ0Av7ImuLZAiwovviR44yIcJXhOJqz2n9yjA8bjGbVFRG64wsWvBIt7nnW_oQp7p_HVT7PyjUyNJOvMa9mXUWhOz5ntEvMGBjNdoK32mcnoJUboihG0Jd6q6pN0y1cFFb8pM2eCezFleCDgDZXW0Re_QWW7EiW991ZXqQ2WNJE='
API_ID = 25897592
API_HASH = '94e48115fc78c3eeca61a4561443f1ef'
# ============================

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

bot_entity = None
sticker_msg_id = None
heyyy_msg_id = None
f_msg_id = None

match_active = False
promo_sent = False
sending_lock = asyncio.Lock()
promo_cancelled = False
finding_lock = asyncio.Lock()
chat_ended = False
finding_timeout_task = None


async def find_sticker():
    global sticker_msg_id, heyyy_msg_id, f_msg_id
    try:
        msgs = await client.get_messages('me', limit=50)
        for m in msgs:
            if m.sticker and not sticker_msg_id:
                sticker_msg_id = m.id
                print("[+] Sticker found!")
            if m.text and m.text.lower() == 'heyyy' and not heyyy_msg_id:
                heyyy_msg_id = m.id
                print("[+] 'heyyy' message found!")
            if m.text and m.text.upper() == 'F' and not f_msg_id:
                f_msg_id = m.id
                print("[+] 'F' message found!")
        
        if all([sticker_msg_id, heyyy_msg_id, f_msg_id]):
            return True
            
    except Exception as e:
        print(f"[!] Find error: {e}")
    
    print("[!] Send 'heyyy', 'F', and sticker to Saved Messages first!")
    return False


async def click_find_partner():
    global match_active, promo_sent, promo_cancelled, chat_ended, finding_timeout_task
    
    if finding_lock.locked():
        print("[*] Already finding partner, skipping...")
        return True
    
    async with finding_lock:
        print("[*] Looking for Find a Partner button...")
        
        try:
            for attempt in range(3):
                msgs = await client.get_messages(bot_entity, limit=10)
                for m in msgs:
                    if not m.reply_markup:
                        continue
                    for row in m.reply_markup.rows:
                        for btn in row.buttons:
                            btn_text = btn.text or ''
                            if 'Find a Partner' in btn_text or 'Find a partner' in btn_text or 'Find' in btn_text:
                                try:
                                    await m.click(text=btn.text)
                                    print(f"[→] Find a Partner clicked (attempt {attempt+1})")
                                    match_active = False
                                    promo_sent = False
                                    promo_cancelled = False
                                    chat_ended = False
                                    await asyncio.sleep(3)
                                    return True
                                except Exception as click_err:
                                    print(f"[!] Click error: {click_err}")
                                    continue
                
                if attempt < 2:
                    print(f"[*] Button not found, waiting... (attempt {attempt+1})")
                    await asyncio.sleep(2)
            
            print("[!] Button not found, using /next fallback")
            await client.send_message(bot_entity, '/next')
            match_active = False
            promo_sent = False
            promo_cancelled = False
            chat_ended = False
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            print(f"[!] Find partner error: {e}")
            match_active = False
            promo_sent = False
            promo_cancelled = False
            chat_ended = False
            await asyncio.sleep(3)
            return True


async def safe_stop_and_find():
    global match_active, promo_sent, chat_ended
    
    if chat_ended:
        print("[*] Chat already ended, skipping /stop")
        await click_find_partner()
        return
    
    if not match_active:
        print("[*] No active match, skipping /stop")
        await click_find_partner()
        return
    
    try:
        await client.send_message(bot_entity, '/stop')
        print("[→] /stop sent")
        chat_ended = True
        match_active = False
        promo_sent = False
        await asyncio.sleep(3)
    except Exception as e:
        print(f"[!] Stop error: {e}")
    
    await click_find_partner()


async def send_promo():
    global promo_sent, promo_cancelled
    
    if sending_lock.locked() or promo_sent:
        print("[*] Already sending or already sent, skipping...")
        return
    
    async with sending_lock:
        promo_cancelled = False
        print("[*] Starting forward sequence...")
        
        try:
            if promo_cancelled:
                print("[!] Promo cancelled before heyyy")
                return
                
            if heyyy_msg_id:
                await client.forward_messages(bot_entity, heyyy_msg_id, 'me')
                print("[+] Forwarded: heyyy")
            else:
                await client.send_message(bot_entity, "heyyy")
                print("[+] Sent: heyyy")
            
            await asyncio.sleep(3)
            
            if promo_cancelled:
                print("[!] Promo cancelled before F")
                return
                
            if f_msg_id:
                await client.forward_messages(bot_entity, f_msg_id, 'me')
                print("[+] Forwarded: F")
            else:
                await client.send_message(bot_entity, "F")
                print("[+] Sent: F")
            
            await asyncio.sleep(3)
            
            if promo_cancelled:
                print("[!] Promo cancelled before sticker")
                return
                
            if sticker_msg_id:
                await client.forward_messages(bot_entity, sticker_msg_id, 'me')
                print("[+] Sticker forwarded!")
            else:
                await client.send_message(bot_entity, "💜 @chatxbt_bot\nhttps://t.me/chatxbt_bot")
                print("[+] Text promo sent!")
            
            promo_sent = True
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"[!] Send error: {e}")
            promo_sent = False


async def handle_finding_timeout():
    global finding_timeout_task
    await asyncio.sleep(10)
    
    print("[!] Finding timeout! No match after 10 seconds.")
    
    if not match_active and not finding_lock.locked():
        try:
            await client.send_message(bot_entity, '/stop')
            print("[→] /stop sent (timeout)")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[!] Timeout /stop error: {e}")
        
        await click_find_partner()
    
    finding_timeout_task = None


def extract_emoji(text):
    """
    Extract emoji from spam check message.
    The message format is: "Click on the button with the image [emoji]"
    """
    lines = text.split('\n')
    for line in lines:
        if 'image' in line.lower() or 'picture' in line.lower():
            emojis = [c for c in line if ord(c) > 127]
            if emojis:
                return emojis[-1]
    
    exclude = {'✅', '✓', '✔', '❌', '⚠️', '🔒', '🔓', '👮', '🛡️', '🔐'}
    emojis = [c for c in text if ord(c) > 127 and c not in exclude]
    if emojis:
        return emojis[-1]
    
    return None


@client.on(events.NewMessage(chats='@AnonZorroBot'))
async def handler(event):
    global match_active, promo_sent, promo_cancelled, chat_ended, finding_timeout_task
    
    text = event.text or ''
    
    if event.out:
        return
    
    # ========== SPAM CHECK / VERIFICATION ==========
    if 'Please pass the spam check' in text or 'spam check' in text.lower():
        print("[*] Spam check detected!")
        
        target_emoji = extract_emoji(text)
        
        if target_emoji and event.message.reply_markup:
            print(f"[*] Target emoji detected: {target_emoji}")
            for row in event.message.reply_markup.rows:
                for btn in row.buttons:
                    if btn.text and target_emoji in btn.text:
                        try:
                            await event.message.click(text=btn.text)
                            print(f"[→] Spam check passed: clicked {btn.text}")
                            return
                        except Exception as e:
                            print(f"[!] Spam check click error: {e}")
        
        if event.message.reply_markup:
            print("[*] Trying all buttons...")
            for row in event.message.reply_markup.rows:
                for btn in row.buttons:
                    try:
                        await event.message.click(text=btn.text)
                        print(f"[→] Clicked spam check button: {btn.text}")
                        await asyncio.sleep(1)
                        return
                    except Exception as e:
                        print(f"[!] Button {btn.text} error: {e}")
        return
    
    # ========== VERIFICATION COMPLETED ==========
    if 'Verification has been successfully completed' in text:
        print("[✓] Verification completed")
        return
    
    # ========== PARTNER ENDED CHAT ==========
    if 'Your partner ended the chat' in text:
        print("[✓] Partner ended chat")
        
        match_active = False
        promo_sent = False
        chat_ended = True
        
        if sending_lock.locked():
            print("[!] Cancelling promo...")
            promo_cancelled = True
            print("[*] Waiting for promo to cancel...")
            for _ in range(50):
                if not sending_lock.locked():
                    break
                await asyncio.sleep(0.1)
        
        await asyncio.sleep(2)
        await click_find_partner()
        return
    
    # ========== WE STOPPED CHAT ==========
    if 'You stopped the chat' in text:
        print("[✓] We stopped the chat")
        match_active = False
        promo_sent = False
        chat_ended = True
        await asyncio.sleep(2)
        await click_find_partner()
        return
    
    # ========== BOT WELCOME / MENU ==========
    if "I'm an anonymous chat bot" in text or 'Use the menu' in text:
        print("[*] Bot welcome/menu shown")
        if match_active:
            print("[!] Desync detected: menu shown while match_active=True")
            match_active = False
            chat_ended = True
        
        if not finding_lock.locked():
            await asyncio.sleep(1)
            await click_find_partner()
        return
    
    # ========== LOOKING FOR PARTNER ==========
    if 'Looking for a partner' in text or 'Finding a partner' in text:
        print("[...] Searching for partner...")
        match_active = False
        promo_sent = False
        chat_ended = False
        
        if finding_timeout_task and not finding_timeout_task.done():
            finding_timeout_task.cancel()
            try:
                await finding_timeout_task
            except asyncio.CancelledError:
                pass
        
        finding_timeout_task = asyncio.create_task(handle_finding_timeout())
        return
    
    # ========== MATCH STARTED ==========
    if 'Partner found, let' in text or "Start chatting" in text:
        print("[+] Match started!")
        match_active = True
        promo_sent = False
        promo_cancelled = False
        chat_ended = False
        
        if finding_timeout_task and not finding_timeout_task.done():
            finding_timeout_task.cancel()
            try:
                await finding_timeout_task
            except asyncio.CancelledError:
                pass
            finding_timeout_task = None
        
        await asyncio.sleep(1)
        await send_promo()
        
        if not promo_cancelled:
            await safe_stop_and_find()
        else:
            print("[!] Promo cancelled, cleaning up...")
            await asyncio.sleep(1)
            await click_find_partner()
        return
    
    # ========== PARTNER SENT MESSAGE DURING MATCH ==========
    if match_active and not sending_lock.locked():
        if promo_sent:
            print("[!] Partner messaging after promo! Skipping...")
            await safe_stop_and_find()
            return
        
        print("[+] Partner sent message/sticker!")
        await send_promo()
        if not promo_cancelled:
            await safe_stop_and_find()
        else:
            print("[!] Promo cancelled, finding next...")
            await asyncio.sleep(1)
            await click_find_partner()
        return


async def main():
    global bot_entity
    await client.start()
    print("[*] xbt1-bot (AnonZorroBot) started!")
    
    bot_entity = await client.get_entity('@AnonZorroBot')
    await find_sticker()
    await click_find_partner()
    
    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())
