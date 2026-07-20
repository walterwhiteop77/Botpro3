from database.file_limit_db import filelimitdb
import pytz
from datetime import datetime, timedelta, time as dtime
from aiohttp import web
from .route import routes
from asyncio import sleep 
from datetime import datetime
from database.users_chats_db import db
from info import URL, PREMIUM_LOGS
from Script import script
import aiohttp
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

async def check_expired_premium(client):
    while 1:
        data = await db.get_expired(datetime.now())
        for user in data:
            user_id = user["id"]
            await db.remove_premium_access(user_id)
            try:
                user = await client.get_users(user_id)
                await client.send_message(
                    chat_id=user_id,
                    text=script.PREMIUM_END_TEXT.format(user.mention)
                )
                await client.send_message(PREMIUM_LOGS, text=f"<b>#Premium_Expire\n\nUser name: {user.mention}\nUser id: <code>{user_id}</code>")
            except Exception as e:
                logging.error("Premium expire notification error: %s", e)
            await sleep(0.5)
        await sleep(1)

async def keep_alive():
    """Keep bot alive by sending periodic pings."""
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(298)
            try:
                async with session.get(URL) as resp:
                    if resp.status != 200:
                        logging.warning(f"⚠️ Ping Error! Status: {resp.status}")
            except Exception as e:
                logging.error(f"❌ Ping Failed: {e}")

async def reset_file_limits_daily():
    """Reset per-user daily file counter at 23:59 IST every day."""
    tz = pytz.timezone("Asia/Kolkata")
    while True:
        now = datetime.now(tz)
        target = tz.localize(datetime.combine(now.date(), dtime(23, 59)))
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            filelimitdb.reset_all_file_limits()
            logging.info("✅ Daily file limits reset for all users.")
        except Exception as e:
            logging.error("Failed to reset daily file limits: %s", e)

