from __future__ import annotations

from pathlib import Path
from telebot import TeleBot, types

from src.config import log, ROOT
from src.common.readers import txt_add


CONSTANTS_TYPES = ["Эмоции", "Теги"]


def _sanitize_folder_name(name: str) -> str:
    name = (name or "").strip()
    allowed = []
    for ch in name:
        if ch.isalnum() or ch in ("_", "-"):
            allowed.append(ch)
    return "".join(allowed) or "UnknownUser"


def _user_folder_from_user(u: types.User) -> str:
    # как и раньше: username -> first+last
    if getattr(u, "username", None):
        return _sanitize_folder_name(u.username)

    first = getattr(u, "first_name", "") or ""
    last = getattr(u, "last_name", "") or ""
    combined = (first + last).strip() or first.strip() or "UnknownUser"
    return _sanitize_folder_name(combined)


def _constants_path_for_user(user_folder: str, type_name: str) -> Path:
    """
    ROOT/data/<user_folder>/emotions.txt или tags.txt
    """
    base = ROOT / "data" / user_folder
    if type_name == "Эмоции":
        return base / "emotions.txt"
    if type_name == "Теги":
        return base / "tags.txt"
    # на всякий
    return base / f"{type_name}.txt"


def register(bot: TeleBot) -> None:

    @bot.message_handler(commands=["edit_constants"])
    def handler(message: types.Message):
        user = message.from_user
        user_folder = _user_folder_from_user(user)

        log.info(f"HANDLE edit_constants | from user: {user} | folder={user_folder}")

        markup = types.InlineKeyboardMarkup()
        for idx, constant_type in enumerate(CONSTANTS_TYPES):
            btn = types.InlineKeyboardButton(
                text=constant_type,
                callback_data=f"edit_constants:{idx}",
            )
            markup.add(btn)

        # прибираем команду
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except Exception:
            pass

        bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=getattr(message, "message_thread_id", None),
            text="Что добавить?",
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_constants:"))
    def ready_to_handle(call: types.CallbackQuery):
        user = call.from_user  # важнее чем call.message.from_user
        user_folder = _user_folder_from_user(user)

        type_idx = int(call.data.split(":")[1])
        type_name = CONSTANTS_TYPES[type_idx]

        log.info(
            f"HANDLE ready_to_handle | from user: {user}, folder={user_folder}, type_name={type_name}"
        )

        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception:
            pass

        bot.send_message(
            chat_id=call.message.chat.id,
            message_thread_id=getattr(call.message, "message_thread_id", None),
            text=f"Введите новые значения для {type_name} через запятую:",
        )

        # тащим user_folder дальше как аргумент
        bot.register_next_step_handler(call.message, handle_values, type_name, user_folder)

    def handle_values(message: types.Message, type_name: str, user_folder: str):
        user = message.from_user
        log.info(
            f"HANDLE handle_values | from user: {user} | folder={user_folder} | type={type_name}"
        )

        text = message.text or ""
        values = [v.strip() for v in text.split(",") if v.strip()]
        payload = "\n".join(values)

        fp = _constants_path_for_user(user_folder, type_name)

        # mkdir надо на папку, а не на файл
        fp.parent.mkdir(parents=True, exist_ok=True)

        if payload:
            txt_add(fp, payload)

        # попробуем убрать промпт "Введите новые значения..."
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
        except Exception:
            pass

        # реакция или ответ
        try:
            bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[types.ReactionTypeEmoji(emoji="👌")],
            )
        except Exception:
            bot.reply_to(message, "Принято 👌")

        # можно ещё сообщить, куда записали
        # bot.reply_to(message, f"Добавил в {fp}")
