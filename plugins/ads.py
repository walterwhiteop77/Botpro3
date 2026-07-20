"""
Set Ads feature (ported from Jisshu-filter-bot).

Admin commands (in bot PM):
  /set_ads {ads name}#{d<days>|i<impressions>}#{photo_url}
      Reply to a text message. That text becomes the ad caption.
      Example:
          /set_ads MyPromo#d7#https://example.com/pic.jpg
          /set_ads MyPromo#i500#https://example.com/pic.jpg

  /del_ads   -> remove the current advertisement.
  /ads       -> show remaining impressions / status of current ad.

When an ad is active, a clickable ads line is injected into every
auto-filter search result. Clicking it opens the bot in DM with the
`?start=ads` deep link which shows the ad photo + caption.
"""

import re
import asyncio
from datetime import datetime, timedelta

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.config_db import mdb
from info import ADMINS


@Client.on_message(filters.private & filters.command("set_ads") & filters.user(ADMINS))
async def set_ads(client, message):
    try:
        if len(message.command) < 2:
            await message.reply_text(
                "Usage: <code>/set_ads {ads name}#{d&lt;days&gt;|i&lt;impressions&gt;}#{photo_url}</code>\n"
                "Reply to the text message you want as ad caption.",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        command_args = message.text.split(maxsplit=1)[1]
        if "#" not in command_args or len(command_args.split("#")) < 3:
            await message.reply_text(
                "Usage: <code>/set_ads {ads name}#{d&lt;days&gt;|i&lt;impressions&gt;}#{photo_url}</code>",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        ads_name, duration_or_impression, url = command_args.split("#", 2)
        ads_name = ads_name.strip()
        url = url.strip()

        if len(ads_name) > 35:
            await message.reply_text("Advertisement name should not exceed 35 characters.")
            return

        if not re.match(r"https?://.+", url):
            await message.reply_text("Invalid URL format. Provide a valid https/http image URL.")
            return

        expiry_date = None
        impression_count = None
        prefix = duration_or_impression[:1]
        value = duration_or_impression[1:]

        if prefix == "d":
            if not value.isdigit():
                await message.reply_text("Duration must be a number, e.g. <code>d7</code>.",
                                         parse_mode=enums.ParseMode.HTML)
                return
            expiry_date = datetime.now() + timedelta(days=int(value))
        elif prefix == "i":
            if not value.isdigit():
                await message.reply_text("Impression count must be a number, e.g. <code>i500</code>.",
                                         parse_mode=enums.ParseMode.HTML)
                return
            impression_count = int(value)
        else:
            await message.reply_text(
                "Invalid prefix. Use <code>d</code> for days or <code>i</code> for impressions.",
                parse_mode=enums.ParseMode.HTML,
            )
            return

        reply = message.reply_to_message
        if not reply or not reply.text:
            await message.reply_text("Reply to a text message that will be used as the ad caption.")
            return

        await mdb.update_advirtisment(
            ads_string=reply.text,
            ads_name=ads_name,
            expiry=expiry_date,
            impression=impression_count,
            ads_link=url,
        )

        await asyncio.sleep(1)
        _, name, imp = await mdb.get_advirtisment()
        detail = f"expires on {expiry_date.strftime('%d %b %Y %H:%M')}" if expiry_date else f"{imp} impressions"
        await message.reply_text(
            f"✅ Advertisement <b>{name}</b> has been set ({detail}).\nPhoto: {url}",
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")


@Client.on_message(filters.private & filters.command("del_ads") & filters.user(ADMINS))
async def del_ads(client, message):
    try:
        current_link = await mdb.get_ads_link()
        await mdb.clear_advertisement()
        if current_link:
            await message.reply_text(f"✅ Advertisement removed. (photo link was: {current_link})",
                                     disable_web_page_preview=True)
        else:
            await message.reply_text("✅ Advertisement reset. No photo link was set.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")


@Client.on_message(filters.private & filters.command("ads"))
async def ads_status(_, message):
    try:
        ads_string, name, impression = await mdb.get_advirtisment()
        if not name:
            await message.reply_text("No ads set.")
            return
        if impression == 0:
            await message.reply_text(f"Advertisement '{name}' has expired.")
            return
        if impression is None:
            await message.reply_text(f"Advertisement '{name}' is active (time-based).")
        else:
            await message.reply_text(f"Advertisement '{name}' has {impression} impressions left.")
    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
