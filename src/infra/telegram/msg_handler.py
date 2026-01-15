from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, List, Set, Optional

from telebot import TeleBot, types

from src.config import log, ROOT
from src.common.readers import txt_read
from src.integrations.gas_client import get_gas_client


TZ = ZoneInfo("Asia/Yekaterinburg")


@dataclass
class UserSession:
    text: str
    first_message_ts: int  # message.date (unix)
    emotions_idx: Set[int] = field(default_factory=set)
    tags_idx: Set[int] = field(default_factory=set)
    step: str = "emotions"  # emotions | tags
    keyboard_message_id: Optional[int] = None
    thread_id: Optional[int] = None

    # ВАЖНО: теперь значения зависят от юзера
    emotions_values: List[str] = field(default_factory=list)
    tags_values: List[str] = field(default_factory=list)

    # полезно для логов/отладки
    user_folder: str = ""


SESSIONS: Dict[int, UserSession] = {}


def _sanitize_folder_name(name: str) -> str:
    """
    Превращает 'Sergey A.Y.' -> 'SergeyAY', убирает мусор.
    Разрешаем буквы/цифры/_/-
    """
    name = (name or "").strip()
    allowed = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-"):
            allowed.append(ch)
    return "".join(allowed) or "UnknownUser"


def _user_folder_from_message(message: types.Message) -> str:
    """
    Как определить папку пользователя:
    1) username (самый стабильный вариант)
    2) first_name + last_name (если username нет)
    """
    u = message.from_user
    if getattr(u, "username", None):
        return _sanitize_folder_name(u.username)

    first = getattr(u, "first_name", "") or ""
    last = getattr(u, "last_name", "") or ""
    combined = (first + last).strip() or first.strip() or "UnknownUser"
    return _sanitize_folder_name(combined)


def _paths_for_user_folder(user_folder: str) -> Dict[str, Path]:
    base = ROOT / "data" / user_folder
    return {
        "Эмоции": base / "emotions.txt",
        "Теги": base / "tags.txt",
    }


def _load_user_constants(user_folder: str) -> tuple[List[str], List[str]]:
    """
    Читает эмоции/теги из папки пользователя.
    Если файлов нет — кидаем понятную ошибку в лог и возвращаем пустые списки.
    """
    paths = _paths_for_user_folder(user_folder)
    emotions_path = paths["Эмоции"]
    tags_path = paths["Теги"]

    emotions: List[str] = []
    tags: List[str] = []

    try:
        emotions = txt_read(emotions_path)
    except Exception as e:
        log.error(f"Can't read emotions file: {emotions_path} | {e}")

    try:
        tags = txt_read(tags_path)
    except Exception as e:
        log.error(f"Can't read tags file: {tags_path} | {e}")

    return emotions, tags


def _format_dt(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _build_grid_keyboard(
    values: List[str],
    selected_idx: Set[int],
    prefix: str,
    done_cb: str,
    cols: int = 3,
) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()

    for i in range(0, len(values), cols):
        row_btns = []
        for idx in range(i, min(i + cols, len(values))):
            text = values[idx]
            if idx in selected_idx:
                text = f"✅ {text}"
            row_btns.append(types.InlineKeyboardButton(text=text, callback_data=f"{prefix}:{idx}"))
        markup.row(*row_btns)

    markup.row(types.InlineKeyboardButton(text="✅ Готово", callback_data=done_cb))
    return markup


def register(bot: TeleBot) -> None:
    @bot.message_handler(content_types=["text"], func=lambda m: True if not getattr(m, "reply_to_message", None) else False)
    def handler(message: types.Message):
        user = message.from_user
        text = message.text or ""
        chat_id = message.chat.id
        thread_id = getattr(message, "message_thread_id", None)


        user_folder = _user_folder_from_message(message)
        emotions_values, tags_values = _load_user_constants(user_folder)

        log.info(f"HANDLE | text={text}; from user: {user} | folder={user_folder}")

        SESSIONS[chat_id] = UserSession(
            text=text,
            first_message_ts=message.date,
            step="emotions",
            thread_id=thread_id,
            emotions_values=emotions_values,
            tags_values=tags_values,
            user_folder=user_folder,
        )
        bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        _send_emotions_step(bot, chat_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("e:") or call.data == "done:e")
    def cb_emotions(call: types.CallbackQuery):
        chat_id = call.message.chat.id
        sess = SESSIONS.get(chat_id)
        if not sess:
            bot.answer_callback_query(call.id, "Сессия не найдена. Пришли текст заново.")
            return

        if call.data == "done:e":
            sess.step = "tags"
            bot.answer_callback_query(call.id, "Ок, к тэгам.")
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
            _send_tags_step(bot, chat_id)
            return

        try:
            idx = int(call.data.split(":")[1])
        except Exception:
            bot.answer_callback_query(call.id, "Не понял кнопку.")
            return

        if idx in sess.emotions_idx:
            sess.emotions_idx.remove(idx)
        else:
            sess.emotions_idx.add(idx)

        markup = _build_grid_keyboard(
            values=sess.emotions_values,
            selected_idx=sess.emotions_idx,
            prefix="e",
            done_cb="done:e",
            cols=3,
        )
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
            )
        except Exception as e:
            log.warning(f"edit_message_reply_markup failed: {e}")

        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("t:") or call.data == "done:t")
    def cb_tags(call: types.CallbackQuery):
        chat_id = call.message.chat.id
        sess = SESSIONS.get(chat_id)
        if not sess:
            bot.answer_callback_query(call.id, "Сессия не найдена. Пришли текст заново.")
            return

        if call.data == "done:t":
            bot.answer_callback_query(call.id, "Готово.")
            bot.delete_message(chat_id=chat_id, message_id=call.message.message_id)
            _finish(bot, chat_id)
            return

        try:
            idx = int(call.data.split(":")[1])
        except Exception:
            bot.answer_callback_query(call.id, "Не понял кнопку.")
            return

        if idx in sess.tags_idx:
            sess.tags_idx.remove(idx)
        else:
            sess.tags_idx.add(idx)

        markup = _build_grid_keyboard(
            values=sess.tags_values,
            selected_idx=sess.tags_idx,
            prefix="t",
            done_cb="done:t",
            cols=3,
        )
        try:
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
            )
        except Exception as e:
            log.warning(f"edit_message_reply_markup failed: {e}")

        bot.answer_callback_query(call.id)


def _send_emotions_step(bot: TeleBot, chat_id: int):
    sess = SESSIONS[chat_id]

    if not sess.emotions_values:
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=sess.thread_id,
            text=f"Не нашёл эмоции для пользователя ({sess.user_folder}). "
                 f"Проверь файл: {ROOT / 'data' / sess.user_folder / 'emotions.txt'}",
        )
        return

    markup = _build_grid_keyboard(
        values=sess.emotions_values,
        selected_idx=sess.emotions_idx,
        prefix="e",
        done_cb="done:e",
        cols=3,
    )
    msg = bot.send_message(
        chat_id=chat_id,
        message_thread_id=sess.thread_id,
        text="Эмоции?",
        reply_markup=markup,
    )
    sess.keyboard_message_id = msg.message_id


def _send_tags_step(bot: TeleBot, chat_id: int):
    sess = SESSIONS[chat_id]

    if not sess.tags_values:
        bot.send_message(
            chat_id=chat_id,
            message_thread_id=sess.thread_id,
            text=f"Не нашёл теги для пользователя ({sess.user_folder}). "
                 f"Проверь файл: {ROOT / 'data' / sess.user_folder / 'tags.txt'}",
        )
        return

    markup = _build_grid_keyboard(
        values=sess.tags_values,
        selected_idx=sess.tags_idx,
        prefix="t",
        done_cb="done:t",
        cols=3,
    )
    msg = bot.send_message(
        chat_id=chat_id,
        message_thread_id=sess.thread_id,
        text="Теги?",
        reply_markup=markup,
    )
    sess.keyboard_message_id = msg.message_id


def _finish(bot: TeleBot, chat_id: int):
    sess = SESSIONS.get(chat_id)
    if not sess:
        return

    emotions = [sess.emotions_values[i] for i in sorted(sess.emotions_idx) if i < len(sess.emotions_values)]
    tags = [sess.tags_values[i] for i in sorted(sess.tags_idx) if i < len(sess.tags_values)]

    summary = (
        f"{sess.text}\n"
        f"Эмоции: {', '.join(emotions) if emotions else '—'}\n"
        f"Теги: {', '.join(tags) if tags else '—'}\n"
        f"{_format_dt(sess.first_message_ts)}"
    )

    log.info(
        "RESULT | "
        f"folder={sess.user_folder}; "
        f"text={sess.text!r}; "
        f"first_ts={sess.first_message_ts}; "
        f"emotions={emotions}; "
        f"tags={tags}"
    )

    result_msg = bot.send_message(chat_id=chat_id, message_thread_id=sess.thread_id, text=summary)

    gas = get_gas_client()
    gas.upsert_note(
        user=sess.user_folder,  # "SergeyAY"
        msg_id=result_msg.message_id,  # это твой "id" в таблице
        when=_format_dt(sess.first_message_ts),  # уже dd.mm...
        what=sess.text,
        emotions=emotions,
        tags=tags,
    )

    del SESSIONS[chat_id]
