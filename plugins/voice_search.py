"""
Voice search: transcribe incoming voice/audio messages and run the same
search flow as a text message. If transcription fails, ask the user to try again.

Uses SpeechRecognition (Google Web Speech, free) with pydub for OGG->WAV
conversion. Requires ffmpeg on the host (already required by other media
handling in this bot).
"""
import os
import asyncio
import logging
import tempfile

from pyrogram import Client, filters

from .pmfilter import auto_filter, give_filter  # noqa: F401
from info import SUPPORT_CHAT_ID

logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr
except Exception as e:  # pragma: no cover
    sr = None
    logger.warning("speech_recognition not available: %s", e)

try:
    from pydub import AudioSegment
except Exception as e:  # pragma: no cover
    AudioSegment = None
    logger.warning("pydub not available: %s", e)


TRANSCRIBE_FAIL_TEXT = (
    "🎙️ ꜱᴏʀʀʏ, ɪ ᴄᴏᴜʟᴅɴ'ᴛ ᴜɴᴅᴇʀꜱᴛᴀɴᴅ ʏᴏᴜʀ ᴠᴏɪᴄᴇ ᴍᴇꜱꜱᴀɢᴇ. "
    "ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ ᴡɪᴛʜ ᴀ ᴄʟᴇᴀʀᴇʀ ʀᴇᴄᴏʀᴅɪɴɢ ᴏʀ ᴛʏᴘᴇ ʏᴏᴜʀ ǫᴜᴇʀʏ."
)

_LANG_CANDIDATES = ["en-IN", "en-US", "hi-IN"]


def _blocking_transcribe(ogg_path: str) -> str:
    """Convert OGG->WAV and run Google recognizer. Returns text or ''. Blocking."""
    if sr is None or AudioSegment is None:
        return ""
    wav_path = ogg_path + ".wav"
    try:
        AudioSegment.from_file(ogg_path).export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        # Try a few common languages; return the first one that works.
        for lang in _LANG_CANDIDATES:
            try:
                text = recognizer.recognize_google(audio, language=lang)
                if text and text.strip():
                    return text.strip()
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                logger.warning("Google STT request error (%s): %s", lang, e)
                continue
        return ""
    except Exception as e:
        logger.exception("Voice transcription failed: %s", e)
        return ""
    finally:
        for p in (ogg_path, wav_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


async def _transcribe_voice(client, message) -> str:
    tmp_dir = tempfile.gettempdir()
    file_path = await message.download(
        file_name=os.path.join(tmp_dir, f"vs_{message.chat.id}_{message.id}.ogg")
    )
    if not file_path:
        return ""
    return await asyncio.to_thread(_blocking_transcribe, file_path)


@Client.on_message(filters.private & (filters.voice | filters.audio) & filters.incoming)
async def pm_voice_search(bot, message):
    status = await message.reply_text("🎙️ ᴛʀᴀɴꜱᴄʀɪʙɪɴɢ ʏᴏᴜʀ ᴠᴏɪᴄᴇ...", quote=True)
    try:
        text = await _transcribe_voice(bot, message)
    except Exception as e:
        logger.exception("PM voice search failed: %s", e)
        text = ""

    if not text:
        try:
            await status.edit_text(TRANSCRIBE_FAIL_TEXT)
        except Exception:
            await message.reply_text(TRANSCRIBE_FAIL_TEXT)
        return

    try:
        await status.edit_text(f"🔎 ꜱᴇᴀʀᴄʜɪɴɢ ꜰᴏʀ: <b>{text}</b>")
    except Exception:
        pass

    # Re-route through the same auto_filter flow used by text messages.
    message.text = text
    try:
        await auto_filter(bot, message)
    except Exception as e:
        logger.exception("auto_filter failed after voice transcription: %s", e)


@Client.on_message(filters.group & (filters.voice | filters.audio) & filters.incoming)
async def group_voice_search(client, message):
    # Only respond to voice searches in groups where auto_ffilter behavior applies
    # (mirrors the text-based group handler).
    try:
        text = await _transcribe_voice(client, message)
    except Exception as e:
        logger.exception("Group voice search failed: %s", e)
        text = ""

    if not text:
        try:
            await message.reply_text(TRANSCRIBE_FAIL_TEXT, quote=True)
        except Exception:
            pass
        return

    message.text = text
    try:
        if message.chat.id == SUPPORT_CHAT_ID:
            # Support-chat path is text-only availability check; skip for voice.
            return
        await auto_filter(client, message)
    except Exception as e:
        logger.exception("auto_filter failed after group voice transcription: %s", e)
