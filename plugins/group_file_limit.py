"""
Group-level File Limit configuration.

Lets a group owner/admin override the global file-limit settings for
their own group without touching the bot's config. Commands work only
inside groups and only for group admins/owners (bot ADMINS always
allowed).

Commands (in a group):
  /filelimit                -> show current effective settings
  /filelimit on             -> force-enable file limit in this group
  /filelimit off            -> disable file limit in this group only
  /filelimit default        -> remove override, inherit global config
  /setfilelimit <N>         -> set this group's daily limit to N (>0)
  /resetgrouplimit          -> reset today's counters for this group
"""

import logging
from pyrogram import Client, filters, enums

from info import ADMINS, IS_FILE_LIMIT, FILES_LIMIT
from utils import is_check_admin
from database.file_limit_db import filelimitdb

logger = logging.getLogger(__name__)


async def _is_group_admin(client, message) -> bool:
    if message.from_user and message.from_user.id in ADMINS:
        return True
    try:
        return await is_check_admin(client, message.chat.id, message.from_user.id)
    except Exception:
        return False


def _status_text(grp_id: int) -> str:
    cfg = filelimitdb.get_group_config(grp_id)
    enabled, limit = filelimitdb.get_effective_limit(grp_id)
    action = filelimitdb.get_effective_action(grp_id)
    if cfg:
        source = "ɢʀᴏᴜᴘ ᴏᴠᴇʀʀɪᴅᴇ"
    else:
        source = "ɢʟᴏʙᴀʟ ᴄᴏɴꜰɪɢ"
    return (
        "<b>📊 ꜰɪʟᴇ ʟɪᴍɪᴛ ꜱᴇᴛᴛɪɴɢꜱ</b>\n\n"
        f"<b>ꜱᴛᴀᴛᴜꜱ:</b> <code>{'ON' if enabled else 'OFF'}</code>\n"
        f"<b>ᴅᴀɪʟʏ ʟɪᴍɪᴛ:</b> <code>{limit}</code>\n"
        f"<b>ᴏᴠᴇʀ-ʟɪᴍɪᴛ ᴀᴄᴛɪᴏɴ:</b> <code>{action}</code>\n"
        f"<b>ꜱᴏᴜʀᴄᴇ:</b> <code>{source}</code>\n"
        f"<b>ɢʟᴏʙᴀʟ ᴅᴇꜰᴀᴜʟᴛ:</b> <code>{'ON' if IS_FILE_LIMIT else 'OFF'} / {FILES_LIMIT}</code>\n\n"
        "<b>ᴜꜱᴀɢᴇ:</b>\n"
        "<code>/filelimit on|off|default</code>\n"
        "<code>/setfilelimit &lt;number&gt;</code>\n"
        "<code>/filelimitaction redirect|verify</code>\n"
        "<code>/resetgrouplimit</code>"
    )


@Client.on_message(filters.command("filelimit") & (filters.group | filters.channel))
async def _grp_filelimit(client, message):
    if not await _is_group_admin(client, message):
        return await message.reply_text(
            "<b>❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴄᴏɴꜰɪɢᴜʀᴇ ᴛʜɪꜱ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    grp_id = message.chat.id

    if len(message.command) == 1:
        return await message.reply_text(
            _status_text(grp_id), parse_mode=enums.ParseMode.HTML
        )

    action = message.command[1].strip().lower()
    if action in ("on", "enable"):
        filelimitdb.set_group_config(grp_id, enabled=True)
        await message.reply_text(
            "<b>✅ ꜰɪʟᴇ ʟɪᴍɪᴛ ᴇɴᴀʙʟᴇᴅ ꜰᴏʀ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    elif action in ("off", "disable"):
        filelimitdb.set_group_config(grp_id, enabled=False)
        await message.reply_text(
            "<b>✅ ꜰɪʟᴇ ʟɪᴍɪᴛ ᴅɪꜱᴀʙʟᴇᴅ ꜰᴏʀ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    elif action in ("default", "reset", "clear", "inherit"):
        filelimitdb.clear_group_config(grp_id)
        await message.reply_text(
            "<b>✅ ᴏᴠᴇʀʀɪᴅᴇ ʀᴇᴍᴏᴠᴇᴅ. ᴜꜱɪɴɢ ɢʟᴏʙᴀʟ ᴄᴏɴꜰɪɢ ɴᴏᴡ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    elif action == "status":
        await message.reply_text(_status_text(grp_id), parse_mode=enums.ParseMode.HTML)
    else:
        return await message.reply_text(
            "<b>❌ ᴜꜱᴀɢᴇ:</b> <code>/filelimit on|off|default|status</code>",
            parse_mode=enums.ParseMode.HTML,
        )


@Client.on_message(filters.command("setfilelimit") & (filters.group | filters.channel))
async def _grp_setfilelimit(client, message):
    if not await _is_group_admin(client, message):
        return await message.reply_text(
            "<b>❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴄᴏɴꜰɪɢᴜʀᴇ ᴛʜɪꜱ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ ᴜꜱᴀɢᴇ:</b> <code>/setfilelimit &lt;number&gt;</code>",
            parse_mode=enums.ParseMode.HTML,
        )
    try:
        n = int(message.command[1])
        if n <= 0 or n > 10000:
            raise ValueError
    except ValueError:
        return await message.reply_text(
            "<b>❌ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴘᴏꜱɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ (1-10000).</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    grp_id = message.chat.id
    # setting a limit implicitly enables the group override
    filelimitdb.set_group_config(grp_id, enabled=True, limit=n)
    await message.reply_text(
        f"<b>✅ ᴅᴀɪʟʏ ꜰɪʟᴇ ʟɪᴍɪᴛ ꜱᴇᴛ ᴛᴏ <code>{n}</code> ꜰᴏʀ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>",
        parse_mode=enums.ParseMode.HTML,
    )


@Client.on_message(filters.command("resetgrouplimit") & (filters.group | filters.channel))
async def _grp_resetgrouplimit(client, message):
    if not await _is_group_admin(client, message):
        return await message.reply_text(
            "<b>❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴄᴏɴꜰɪɢᴜʀᴇ ᴛʜɪꜱ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    grp_id = message.chat.id
    try:
        filelimitdb.reset_all_file_limits(group_id=grp_id)
        await message.reply_text(
            "<b>✅ ᴀʟʟ ᴜꜱᴇʀꜱ' ᴄᴏᴜɴᴛᴇʀꜱ ʀᴇꜱᴇᴛ ꜰᴏʀ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("resetgrouplimit failed: %s", e)
        await message.reply_text(
            f"<b>❌ ᴇʀʀᴏʀ: {e}</b>", parse_mode=enums.ParseMode.HTML
        )


@Client.on_message(filters.command("filelimitaction") & (filters.group | filters.channel))
async def _grp_filelimit_action(client, message):
    if not await _is_group_admin(client, message):
        return await message.reply_text(
            "<b>❌ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴄᴏɴꜰɪɢᴜʀᴇ ᴛʜɪꜱ.</b>",
            parse_mode=enums.ParseMode.HTML,
        )
    if len(message.command) < 2:
        current = filelimitdb.get_effective_action(message.chat.id)
        return await message.reply_text(
            "<b>📊 ᴏᴠᴇʀ-ʟɪᴍɪᴛ ᴀᴄᴛɪᴏɴ</b>\n\n"
            f"<b>ᴄᴜʀʀᴇɴᴛ:</b> <code>{current}</code>\n\n"
            "<b>ᴜꜱᴀɢᴇ:</b> <code>/filelimitaction redirect|verify</code>\n\n"
            "• <b>redirect</b> — ꜱʜᴏᴡ ᴅᴏᴡɴʟᴏᴀᴅ-ɴᴏᴡ + ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ ʙᴜᴛᴛᴏɴꜱ\n"
            "• <b>verify</b> — ꜰᴏʀᴄᴇ ᴜꜱᴇʀ ᴛʜʀᴏᴜɢʜ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴀɢᴀɪɴ, ᴛʜᴇɴ ᴄᴏɴᴛɪɴᴜᴇ",
            parse_mode=enums.ParseMode.HTML,
        )
    act = message.command[1].strip().lower()
    if act not in ("redirect", "verify"):
        return await message.reply_text(
            "<b>❌ ᴜꜱᴀɢᴇ:</b> <code>/filelimitaction redirect|verify</code>",
            parse_mode=enums.ParseMode.HTML,
        )
    filelimitdb.set_group_config(message.chat.id, action=act)
    await message.reply_text(
        f"<b>✅ ᴏᴠᴇʀ-ʟɪᴍɪᴛ ᴀᴄᴛɪᴏɴ ꜱᴇᴛ ᴛᴏ <code>{act}</code> ꜰᴏʀ ᴛʜɪꜱ ɢʀᴏᴜᴘ.</b>",
        parse_mode=enums.ParseMode.HTML,
    )
