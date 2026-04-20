import os
import logging
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)
from sheets import SheetsManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Состояния ────────────────────────────────────────────────────────────────
(
    MAIN_MENU,
    ADD_NAME, ADD_VARIETY, ADD_ROOT, ADD_PRICE, ADD_PURCHASE_DATE, ADD_NOTES,
    SALE_SEARCH, SALE_SELECT, SALE_TYPE, SALE_PRICE, SALE_DATE,
    FIND_SEARCH,
    LIST_FILTER,
    EDIT_SEARCH, EDIT_SELECT_FLOWER, EDIT_FIELD, EDIT_VALUE, EDIT_CONFIRM,
    DELETE_CONFIRM,
) = range(20)

sheets = SheetsManager()


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["➕ Добавить цветок", "💰 Записать продажу"],
            ["🔍 Найти цветок",    "📋 Список цветов"],
            ["✏️ Редактировать",   "💵 Финансы"],
        ],
        resize_keyboard=True,
    )


def _valid_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%d.%m.%Y")
        return True
    except ValueError:
        return False


# ── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Это бот для учёта цветов 🌸\nВыбери действие:",
        reply_markup=main_keyboard(),
    )
    return MAIN_MENU


# ── Главное меню ─────────────────────────────────────────────────────────────
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "➕ Добавить цветок":
        await update.message.reply_text(
            "Введи название цветка:", reply_markup=ReplyKeyboardRemove()
        )
        return ADD_NAME

    elif text == "💰 Записать продажу":
        await update.message.reply_text(
            "Введи название цветка:", reply_markup=ReplyKeyboardRemove()
        )
        return SALE_SEARCH

    elif text == "🔍 Найти цветок":
        await update.message.reply_text(
            "Введи название цветка:", reply_markup=ReplyKeyboardRemove()
        )
        return FIND_SEARCH

    elif text == "📋 Список цветов":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Все",       callback_data="list_all"),
                InlineKeyboardButton("Живые",     callback_data="list_живой"),
            ],
            [
                InlineKeyboardButton("Проданные", callback_data="list_продан"),
                InlineKeyboardButton("Умершие",   callback_data="list_умер"),
            ],
        ])
        await update.message.reply_text("Показать какие?", reply_markup=kb)
        return LIST_FILTER

    elif text == "✏️ Редактировать":
        await update.message.reply_text(
            "Введи название цветка:", reply_markup=ReplyKeyboardRemove()
        )
        return EDIT_SEARCH

    elif text == "💵 Финансы":
        s = sheets.get_financial_summary()
        profit = s["profit"]
        profit_emoji = "📈" if profit >= 0 else "📉"
        await update.message.reply_text(
            f"💵 Финансы\n\n"
            f"🌸 Всего цветков: {s['flower_count']}\n"
            f"🟢 Живых: {s['alive_count']}\n"
            f"💸 Проданных: {s['sold_count']}\n"
            f"🔴 Умерших: {s['dead_count']}\n\n"
            f"💰 Потрачено: {s['total_spent']:.0f} руб.\n"
            f"💵 Заработано: {s['total_earned']:.0f} руб.\n"
            f"{profit_emoji} Баланс: {profit:+.0f} руб.",
            reply_markup=main_keyboard(),
        )
        return MAIN_MENU

    else:
        await update.message.reply_text(
            "Выбери действие из меню 👇", reply_markup=main_keyboard()
        )
        return MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
# ➕ ДОБАВИТЬ ЦВЕТОК
# ═══════════════════════════════════════════════════════════════════════════════
async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["flower"] = {"name": update.message.text.strip()}
    await update.message.reply_text("Сорт?")
    return ADD_VARIETY


async def add_variety(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["flower"]["variety"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("ОКС", callback_data="root_окс"),
        InlineKeyboardButton("ЗКС", callback_data="root_зкс"),
    ]])
    await update.message.reply_text("Корневая система?", reply_markup=kb)
    return ADD_ROOT


async def add_root(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    root = "ОКС" if query.data == "root_окс" else "ЗКС"
    context.user_data["flower"]["root"] = root
    await query.edit_message_text(f"Корневая система: {root}")
    await query.message.reply_text("Цена покупки (руб)?")
    return ADD_PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip().replace(",", "."))
    except ValueError:
        await update.message.reply_text("Введи число, например: 350")
        return ADD_PRICE
    context.user_data["flower"]["purchase_price"] = price
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Сегодня", callback_data="pd_today")
    ]])
    await update.message.reply_text(
        "Дата покупки? (дд.мм.гггг или кнопка)", reply_markup=kb
    )
    return ADD_PURCHASE_DATE


async def add_purchase_date_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = datetime.now().strftime("%d.%m.%Y")
    context.user_data["flower"]["purchase_date"] = today
    await query.edit_message_text(f"Дата покупки: {today}")
    return await _ask_notes(query.message)


async def add_purchase_date_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    if not _valid_date(date_str):
        await update.message.reply_text("Формат: дд.мм.гггг. Попробуй ещё раз:")
        return ADD_PURCHASE_DATE
    context.user_data["flower"]["purchase_date"] = date_str
    return await _ask_notes(update.message)


async def _ask_notes(message):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Пропустить", callback_data="notes_skip")
    ]])
    await message.reply_text(
        "Заметки? (любой текст или пропусти)", reply_markup=kb
    )
    return ADD_NOTES


async def add_notes_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["flower"]["notes"] = update.message.text.strip()
    return await _save_flower(update.message, context)


async def add_notes_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["flower"]["notes"] = ""
    await query.edit_message_text("Заметки: —")
    return await _save_flower(query.message, context)


async def _save_flower(message, context):
    f = context.user_data["flower"]
    sheets.add_flower(f)
    notes_line = f"\nЗаметки: {f['notes']}" if f.get("notes") else ""
    await message.reply_text(
        f"✅ Цветок добавлен!\n\n"
        f"🌸 {f['name']} ({f['variety']})\n"
        f"Корневая система: {f['root']}\n"
        f"Куплен: {f['purchase_date']} за {f['purchase_price']} руб.\n"
        f"Статус: 🟢 живой"
        f"{notes_line}",
        reply_markup=main_keyboard(),
    )
    context.user_data.clear()
    return MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
# 💰 ЗАПИСАТЬ ПРОДАЖУ
# ═══════════════════════════════════════════════════════════════════════════════
async def sale_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flowers = sheets.find_flowers(update.message.text.strip(), status_filter=["живой"])
    if not flowers:
        await update.message.reply_text(
            "Живых цветов с таким названием не нашла.\nПопробуй ещё раз или /start"
        )
        return SALE_SEARCH

    if len(flowers) == 1:
        context.user_data["sale_flower"] = flowers[0]
        return await _ask_sale_type(update.message)

    context.user_data["found"] = {f["id"]: f for f in flowers}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{f['name']} {f['variety']}", callback_data=f"ss_{f['id']}"
        )] for f in flowers
    ])
    await update.message.reply_text("Нашла несколько, выбери:", reply_markup=kb)
    return SALE_SELECT


async def sale_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    flower_id = query.data[3:]
    context.user_data["sale_flower"] = context.user_data["found"][flower_id]
    f = context.user_data["sale_flower"]
    await query.edit_message_text(f"Выбран: {f['name']} {f['variety']}")
    return await _ask_sale_type(query.message)


async def _ask_sale_type(message):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Целиком",   callback_data="st_целиком"),
            InlineKeyboardButton("Черенком",  callback_data="st_черенком"),
        ],
        [
            InlineKeyboardButton("Отростком", callback_data="st_отростком"),
            InlineKeyboardButton("Листом",    callback_data="st_листом"),
        ],
    ])
    await message.reply_text("Тип продажи?", reply_markup=kb)
    return SALE_TYPE


async def sale_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["sale_type"] = query.data[3:]
    await query.edit_message_text(f"Тип продажи: {query.data[3:]}")
    await query.message.reply_text("Цена продажи (руб)?")
    return SALE_PRICE


async def sale_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip().replace(",", "."))
    except ValueError:
        await update.message.reply_text("Введи число, например: 500")
        return SALE_PRICE
    context.user_data["sale_price"] = price
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Сегодня", callback_data="sd_today")
    ]])
    await update.message.reply_text(
        "Дата продажи? (дд.мм.гггг или кнопка)", reply_markup=kb
    )
    return SALE_DATE


async def sale_date_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = datetime.now().strftime("%d.%m.%Y")
    context.user_data["sale_date"] = today
    await query.edit_message_text(f"Дата продажи: {today}")
    return await _save_sale(query.message, context)


async def sale_date_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    if not _valid_date(date_str):
        await update.message.reply_text("Формат: дд.мм.гггг. Попробуй ещё раз:")
        return SALE_DATE
    context.user_data["sale_date"] = date_str
    return await _save_sale(update.message, context)


async def _save_sale(message, context):
    f       = context.user_data["sale_flower"]
    s_type  = context.user_data["sale_type"]
    price   = context.user_data["sale_price"]
    date    = context.user_data["sale_date"]

    sheets.add_sale(f["id"], f["name"], s_type, price, date)

    if s_type == "целиком":
        sheets.update_flower_field(f["id"], "status", "продан")
        status_note = "Статус изменён на: 💸 продан"
    else:
        status_note = "Цветок остался в наличии: 🟢 живой"

    await message.reply_text(
        f"✅ Продажа записана!\n\n"
        f"🌸 {f['name']} {f['variety']}\n"
        f"Тип: {s_type}\n"
        f"Цена: {price} руб.\n"
        f"Дата: {date}\n"
        f"{status_note}",
        reply_markup=main_keyboard(),
    )
    context.user_data.clear()
    return MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
# 🔍 НАЙТИ ЦВЕТОК
# ═══════════════════════════════════════════════════════════════════════════════
async def find_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flowers = sheets.find_flowers(update.message.text.strip())
    if not flowers:
        await update.message.reply_text(
            "Цветок не найден.", reply_markup=main_keyboard()
        )
        return MAIN_MENU

    status_emoji = {"живой": "🟢", "умер": "🔴", "продан": "💸"}

    for f in flowers[:5]:
        sales = sheets.get_flower_sales(f["id"])
        sales_text = ""
        if sales:
            sales_text = "\n\nПродажи:"
            for s in sales:
                sales_text += f"\n• {s['type']} — {s['price']} руб. ({s['date']})"

        notes_line = f"\nЗаметки: {f['notes']}" if f.get("notes") else ""
        emoji = status_emoji.get(f["status"], "❓")

        text = (
            f"🌸 {f['name']} {f['variety']}\n"
            f"Корневая система: {f['root']}\n"
            f"Куплен: {f['purchase_date'] or '—'} за {f['purchase_price']} руб.\n"
            f"Статус: {emoji} {f['status']}"
            f"{notes_line}"
            f"{sales_text}"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"ef_{f['id']}"),
            InlineKeyboardButton("🗑️ Удалить",       callback_data=f"df_{f['id']}"),
        ]])
        await update.message.reply_text(text, reply_markup=kb)

    await update.message.reply_text("Меню:", reply_markup=main_keyboard())
    return MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
# 📋 СПИСОК ЦВЕТОВ
# ═══════════════════════════════════════════════════════════════════════════════
async def list_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    filter_val = query.data[5:]
    status_filter = None if filter_val == "all" else [filter_val]
    flowers = sheets.get_all_flowers(status_filter)

    if not flowers:
        await query.edit_message_text("Цветов не найдено.")
        await query.message.reply_text("Меню:", reply_markup=main_keyboard())
        return MAIN_MENU

    status_emoji = {"живой": "🟢", "умер": "🔴", "продан": "💸"}
    lines = [
        f"{status_emoji.get(f['status'], '❓')} {f['name']} {f['variety']}"
        for f in flowers
    ]
    await query.edit_message_text("Цветы:\n\n" + "\n".join(lines))
    await query.message.reply_text("Меню:", reply_markup=main_keyboard())
    return MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
# ✏️ РЕДАКТИРОВАТЬ
# ═══════════════════════════════════════════════════════════════════════════════
async def edit_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flowers = sheets.find_flowers(update.message.text.strip())
    if not flowers:
        await update.message.reply_text(
            "Цветок не найден.", reply_markup=main_keyboard()
        )
        return MAIN_MENU

    if len(flowers) == 1:
        context.user_data["edit_flower"] = flowers[0]
        return await _ask_edit_field(update.message)

    context.user_data["found"] = {f["id"]: f for f in flowers}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{f['name']} {f['variety']}", callback_data=f"es_{f['id']}"
        )] for f in flowers
    ])
    await update.message.reply_text("Нашла несколько, выбери:", reply_markup=kb)
    return EDIT_SELECT_FLOWER


async def edit_select_flower(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    flower_id = query.data[3:]
    context.user_data["edit_flower"] = context.user_data["found"][flower_id]
    f = context.user_data["edit_flower"]
    await query.edit_message_text(f"Редактируем: {f['name']} {f['variety']}")
    return await _ask_edit_field(query.message)


async def edit_from_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    flower = sheets.get_flower_by_id(query.data[3:])
    if not flower:
        await query.answer("Цветок не найден", show_alert=True)
        return MAIN_MENU
    context.user_data["edit_flower"] = flower
    return await _ask_edit_field(query.message)


async def _ask_edit_field(message):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Название",         callback_data="efl_name"),
            InlineKeyboardButton("Сорт",             callback_data="efl_variety"),
        ],
        [
            InlineKeyboardButton("Корневая система", callback_data="efl_root"),
            InlineKeyboardButton("Цена покупки",     callback_data="efl_purchase_price"),
        ],
        [
            InlineKeyboardButton("Дата покупки",     callback_data="efl_purchase_date"),
            InlineKeyboardButton("Статус",           callback_data="efl_status"),
        ],
        [
            InlineKeyboardButton("Заметки",          callback_data="efl_notes"),
        ],
    ])
    await message.reply_text("Что меняем?", reply_markup=kb)
    return EDIT_FIELD


async def edit_field_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data[4:]
    context.user_data["edit_field"] = field

    if field == "root":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("ОКС", callback_data="ev_ОКС"),
            InlineKeyboardButton("ЗКС", callback_data="ev_ЗКС"),
        ]])
        await query.edit_message_text("Корневая система:", reply_markup=kb)
        return EDIT_VALUE

    if field == "status":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🟢 Живой",  callback_data="ev_живой"),
            InlineKeyboardButton("🔴 Умер",   callback_data="ev_умер"),
            InlineKeyboardButton("💸 Продан", callback_data="ev_продан"),
        ]])
        await query.edit_message_text("Новый статус:", reply_markup=kb)
        return EDIT_VALUE

    labels = {
        "name":           "название",
        "variety":        "сорт",
        "purchase_price": "цену покупки (число)",
        "purchase_date":  "дату покупки (дд.мм.гггг)",
        "notes":          "заметки",
    }
    await query.edit_message_text(f"Введи новое {labels.get(field, field)}:")
    return EDIT_VALUE


# Кнопочный выбор (root, status) → сразу сохраняем
async def edit_value_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    new_value = query.data[3:]
    await query.edit_message_text(f"Новое значение: {new_value}")
    return await _save_edit(query.message, context, new_value)


# Текстовый ввод → показываем кнопку «Готово»
async def edit_value_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_value = update.message.text.strip()
    field = context.user_data.get("edit_field", "")

    if field == "purchase_date":
        if not _valid_date(new_value):
            await update.message.reply_text("Формат: дд.мм.гггг. Попробуй ещё раз:")
            return EDIT_VALUE

    if field == "purchase_price":
        try:
            float(new_value.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Введи число, например: 350")
            return EDIT_VALUE

    context.user_data["edit_pending_value"] = new_value
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Готово",        callback_data="ec_yes"),
        InlineKeyboardButton("✏️ Ввести заново", callback_data="ec_no"),
    ]])
    await update.message.reply_text(
        f"Новое значение: {new_value}", reply_markup=kb
    )
    return EDIT_CONFIRM


async def edit_confirm_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    new_value = context.user_data.get("edit_pending_value")
    await query.edit_message_text(f"Сохраняю: {new_value}")
    return await _save_edit(query.message, context, new_value)


async def edit_confirm_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = context.user_data.get("edit_field", "")
    labels = {
        "name":           "название",
        "variety":        "сорт",
        "purchase_price": "цену покупки (число)",
        "purchase_date":  "дату покупки (дд.мм.гггг)",
        "notes":          "заметки",
    }
    await query.edit_message_text(f"Введи новое {labels.get(field, field)}:")
    return EDIT_VALUE


async def _save_edit(message, context, new_value):
    flower = context.user_data.get("edit_flower")
    field  = context.user_data.get("edit_field")

    if not flower or not field:
        await message.reply_text(
            "Что-то пошло не так. Начни заново /start",
            reply_markup=main_keyboard()
        )
        context.user_data.clear()
        return MAIN_MENU

    sheets.update_flower_field(flower["id"], field, new_value)
    await message.reply_text(
        f"✅ Изменено!\n🌸 {flower['name']} {flower['variety']}",
        reply_markup=main_keyboard(),
    )
    context.user_data.clear()
    return MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════════════
# 🗑️ УДАЛИТЬ
# ═══════════════════════════════════════════════════════════════════════════════
async def delete_from_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    flower = sheets.get_flower_by_id(query.data[3:])
    if not flower:
        await query.answer("Цветок не найден", show_alert=True)
        return MAIN_MENU
    context.user_data["delete_flower"] = flower
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Да, удалить", callback_data="del_yes"),
        InlineKeyboardButton("Отмена",      callback_data="del_no"),
    ]])
    await query.message.reply_text(
        f"Удалить «{flower['name']} {flower['variety']}»?\nДействие необратимо.",
        reply_markup=kb,
    )
    return DELETE_CONFIRM


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    flower = context.user_data.get("delete_flower")
    if flower:
        sheets.delete_flower(flower["id"])
        await query.edit_message_text(
            f"🗑️ {flower['name']} {flower['variety']} удалён."
        )
    await query.message.reply_text("Меню:", reply_markup=main_keyboard())
    context.user_data.clear()
    return MAIN_MENU


async def delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Удаление отменено.")
    await query.message.reply_text("Меню:", reply_markup=main_keyboard())
    return MAIN_MENU


# ── Отмена ───────────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_keyboard())
    return MAIN_MENU


# ── Запуск ───────────────────────────────────────────────────────────────────
def main():
    token = os.environ["TELEGRAM_TOKEN"]
    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler),
                CallbackQueryHandler(list_filter,      pattern=r"^list_"),
                CallbackQueryHandler(edit_from_find,   pattern=r"^ef_"),
                CallbackQueryHandler(delete_from_find, pattern=r"^df_"),
            ],
            # Добавить цветок
            ADD_NAME:          [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_VARIETY:       [MessageHandler(filters.TEXT & ~filters.COMMAND, add_variety)],
            ADD_ROOT:          [CallbackQueryHandler(add_root, pattern=r"^root_")],
            ADD_PRICE:         [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
            ADD_PURCHASE_DATE: [
                CallbackQueryHandler(add_purchase_date_btn, pattern=r"^pd_today$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_purchase_date_text),
            ],
            ADD_NOTES: [
                CallbackQueryHandler(add_notes_skip, pattern=r"^notes_skip$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_notes_text),
            ],
            # Продажа
            SALE_SEARCH:  [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_search)],
            SALE_SELECT:  [CallbackQueryHandler(sale_select, pattern=r"^ss_")],
            SALE_TYPE:    [CallbackQueryHandler(sale_type,   pattern=r"^st_")],
            SALE_PRICE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_price)],
            SALE_DATE: [
                CallbackQueryHandler(sale_date_btn, pattern=r"^sd_today$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sale_date_text),
            ],
            # Найти
            FIND_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_search)],
            # Список
            LIST_FILTER: [CallbackQueryHandler(list_filter, pattern=r"^list_")],
            # Редактировать
            EDIT_SEARCH:        [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_search)],
            EDIT_SELECT_FLOWER: [CallbackQueryHandler(edit_select_flower, pattern=r"^es_")],
            EDIT_FIELD:         [CallbackQueryHandler(edit_field_select,  pattern=r"^efl_")],
            EDIT_VALUE: [
                CallbackQueryHandler(edit_value_btn,  pattern=r"^ev_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_text),
            ],
            EDIT_CONFIRM: [
                CallbackQueryHandler(edit_confirm_yes, pattern=r"^ec_yes$"),
                CallbackQueryHandler(edit_confirm_no,  pattern=r"^ec_no$"),
            ],
            # Удалить
            DELETE_CONFIRM: [
                CallbackQueryHandler(delete_confirm, pattern=r"^del_yes$"),
                CallbackQueryHandler(delete_cancel,  pattern=r"^del_no$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start",  start),
        ],
    )

    app.add_handler(conv)
    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
