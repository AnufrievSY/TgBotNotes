import re
from typing import List

from telebot import TeleBot, types

from src.config import log
from src.integrations.gas_client import get_gas_client
from src.infra.yandex_music.get_info import get_track_meta

YANDEX_MUSIC_RE = re.compile(
    r"https?://(?:music\.)?yandex\.(?:ru|com)/[^\s]+|https?://yandex\.(?:ru|com)/music/[^\s]+",
    flags=re.IGNORECASE,
)

def extract_yandex_music_links(text: str) -> List[str]:
    if not text:
        return []
    return YANDEX_MUSIC_RE.findall(text)

def _user_folder_from_message(message: types.Message) -> str:
    # ВАЖНО: должен совпадать с тем, что используешь в msg_handler/edit_constants.
    u = message.from_user
    if getattr(u, "username", None):
        return u.username  # если у тебя sanitize — используй тот же sanitize
    first = getattr(u, "first_name", "") or ""
    last = getattr(u, "last_name", "") or ""
    return (first + last).strip() or first or "UnknownUser"

def register(bot: TeleBot) -> None:
    @bot.message_handler(
        content_types=["text"],
        func=lambda m: getattr(m, "reply_to_message", None) is not None
    )
    def on_reply(message: types.Message):
        chat_id = message.chat.id
        replied_mid = message.reply_to_message.message_id
        text = message.text or ""

        user_folder = _user_folder_from_message(message)
        gas = get_gas_client()

        # Это reply на нашу запись?
        if not gas.exists(user=user_folder, msg_id=replied_mid):
            return

        links = extract_yandex_music_links(text)
        if not links:
            bot.reply_to(message, "Ссылок Яндекс.Музыки не вижу.")
            return

        items_links = []
        for l in links:
            track_meta = get_track_meta(l)
            items_links.append({"link": l, "text": f"{track_meta[0]} - {track_meta[1]}"})
        resp = gas.add_tracks(user=user_folder, msg_id=replied_mid, items=items_links)
        if not resp.get("ok"):
            bot.reply_to(message, f"Не смог записать в таблицу: {resp.get('error')}")
            return

        added = int(resp.get("added", 0))

        reply_text = message.reply_to_message.text or ""

        msg_links = []
        if message.reply_to_message.any_entities:
            for e in message.reply_to_message.entities:
                if e.type == "text_link":
                    e_text = message.reply_to_message.text[e.offset:e.offset + e.length]
                    msg_links.append(f'<a href="{e.url}">{e_text}</a>')
        for l in links:
            track_meta = get_track_meta(l)
            msg_links.append(f'<a href="{l}">{track_meta[0]} - {track_meta[1]}</a>')
        if 'Плейлист' in reply_text:
            reply_text = reply_text.split('\n\nПлейлист:')[0]
        reply_text += f'\n\nПлейлист:\n{'\n'.join(msg_links)}'
        bot.edit_message_text(chat_id=chat_id, message_id=replied_mid, text=reply_text, disable_web_page_preview=True, parse_mode='HTML')
        bot.delete_message(chat_id=chat_id, message_id=message.message_id)


        log.info(f"PLAYLIST_ADD | chat_id={chat_id} id={replied_mid} links={links} added={added}")
