
import os
import json
import logging
import sqlite3

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from market import get_crypto_candles, ASSETS, TIMEFRAMES
from chart import create_chart

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID = int(os.environ["GROUP_CHAT_ID"])
PRESIDENT_ID = int(os.environ["PRESIDENT_ID"])
MEMBERS = json.loads(os.environ["MEMBER_IDS_JSON"])

NAMES = {
    "ari": "ئاری",
    "suhaib": "سوهەیب",
    "gailan": "گەیلان",
    "sabr": "سەبر",
    "muhammad": "محمد",
    "saman": "سامان",
    "arian": "ئاریان",
    "sam": "سام",
}

DB = "hta_team.db"


def setup_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                president_id INTEGER,
                direction TEXT,
                sl REAL
            )
        """)


def member_key(user_id):
    for key, value in MEMBERS.items():
        if int(value) == user_id:
            return key
    return None


def home_keyboard():
    rows = []
    for key, name in NAMES.items():
        rows.append([
            InlineKeyboardButton(name, callback_data=f"member:{key}")
        ])
    return InlineKeyboardMarkup(rows)


def asset_keyboard():
    rows = []
    for symbol, name in ASSETS.items():
        rows.append([
            InlineKeyboardButton(
                f"{name} ({symbol})",
                callback_data=f"asset:{symbol}"
            )
        ])
    return InlineKeyboardMarkup(rows)


def timeframe_keyboard(symbol):
    rows = []
    for tf in TIMEFRAMES:
        rows.append([
            InlineKeyboardButton(
                tf,
                callback_data=f"tf:{symbol}:{tf}"
            )
        ])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == PRESIDENT_ID:
        await update.message.reply_text(
            "بەخێربێیت هەردی، سەرۆکی HTA TEAM.",
            reply_markup=asset_keyboard()
        )
        return

    await update.message.reply_text(
        "HTA TEAM\ncreate by : suhaib\n\nناوی خۆت هەڵبژێرە:",
        reply_markup=home_keyboard()
    )


async def charts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == PRESIDENT_ID or member_key(user_id):
        await update.message.reply_text(
            "ئەم ئەستەکانە هەڵبژێرە:",
            reply_markup=asset_keyboard()
        )
    else:
        await update.message.reply_text("دەستپێگەیشتنت نییە.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("member:"):
        key = data.split(":")[1]
        if MEMBERS.get(key) is None or int(MEMBERS[key]) != user_id:
            await query.answer("ئەم ناوە هی تۆ نییە.", show_alert=True)
            return
        context.user_data["member"] = key
        await query.edit_message_text(
            f"بەخێربێیت {NAMES[key]}، ئەستەک هەڵبژێرە:",
            reply_markup=asset_keyboard()
        )
        return

    if data.startswith("asset:"):
        if user_id != PRESIDENT_ID and not member_key(user_id):
            return
        symbol = data.split(":")[1]
        context.user_data["symbol"] = symbol
        await query.edit_message_text(
            f"{ASSETS[symbol]} - {symbol}\nکاتی چارت هەڵبژێرە:",
            reply_markup=timeframe_keyboard(symbol)
        )
        return

    if data.startswith("tf:"):
        if user_id != PRESIDENT_ID and not member_key(user_id):
            return

        _, symbol, tf = data.split(":")
        await query.edit_message_text("چارت ئامادە دەکرێت...")

        try:
            candles = await get_crypto_candles(symbol, tf)
            filename = create_chart(candles, ASSETS[symbol], symbol, tf)

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("BUY", callback_data=f"signal:BUY:{symbol}:{tf}"),
                    InlineKeyboardButton("SELL", callback_data=f"signal:SELL:{symbol}:{tf}")
                ]
            ])

            with open(filename, "rb") as photo:
                sent = await context.bot.send_photo(
                    chat_id=GROUP_CHAT_ID,
                    photo=photo,
                    caption=f"{ASSETS[symbol]} ({symbol}) | {tf}",
                    reply_markup=keyboard
                )

            context.user_data["last_chart"] = {
                "message_id": sent.message_id,
                "symbol": symbol,
                "tf": tf
            }

        except Exception:
            logging.exception("Chart generation failed")
            await query.message.reply_text("هەڵەیەک ڕوویدا. دواتر هەوڵ بدەرەوە.")


async def signal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != PRESIDENT_ID:
        await query.answer("تەنها سەرۆک دەتوانێت سیگناڵ بدات.", show_alert=True)
        return

    await query.answer()
    _, direction, symbol, tf = query.data.split(":")
    context.user_data["pending_signal"] = {
        "direction": direction,
        "symbol": symbol,
        "tf": tf,
        "message_id": query.message.message_id
    }

    await query.message.reply_text(
        f"Stop Loss بە چەند ٪ دابنێ؟ بۆ نموونە 2"
    )


async def sl_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != PRESIDENT_ID:
        return

    pending = context.user_data.get("pending_signal")
    if not pending:
        return

    try:
        sl = float(update.message.text.replace("%", "").strip())
        if not 0 < sl <= 100:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("تکایە ژمارەیەکی دروست بنووسە، وەک 2")
        return

    pending["sl"] = sl

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("پشتڕاستکردنەوە", callback_data="confirm_signal"),
            InlineKeyboardButton("هەڵوەشاندنەوە", callback_data="cancel_signal")
        ]
    ])

    await update.message.reply_text(
        f"سیگناڵ:\n{pending['symbol']}\n"
        f"Timeframe: {pending['tf']}\n"
        f"Direction: {pending['direction']}\n"
        f"Stop Loss: {sl}%",
        reply_markup=keyboard
    )


async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != PRESIDENT_ID:
        await query.answer("تەنها سەرۆک دەتوانێت پشتڕاستی بکاتەوە.", show_alert=True)
        return

    pending = context.user_data.get("pending_signal")
    if not pending:
        await query.answer("سیگناڵێکی چالاک نییە.", show_alert=True)
        return

    await query.answer()

    with sqlite3.connect(DB) as conn:
        conn.execute(
            """INSERT INTO pending_signals
            (chat_id, message_id, president_id, direction, sl)
            VALUES (?, ?, ?, ?, ?)""",
            (
                GROUP_CHAT_ID,
                pending["message_id"],
                PRESIDENT_ID,
                pending["direction"],
                pending["sl"]
            )
        )

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=(
            f"📢 HTA TEAM SIGNAL\n"
            f"Asset: {pending['symbol']}\n"
            f"Timeframe: {pending['tf']}\n"
            f"Direction: {pending['direction']}\n"
            f"Stop Loss: {pending['sl']}%"
        ),
        reply_to_message_id=pending["message_id"]
    )

    context.user_data.pop("pending_signal", None)
    await query.edit_message_text("سیگناڵەکە بڵاوکرایەوە.")


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != PRESIDENT_ID:
        await query.answer("تەنها سەرۆک دەتوانێت هەڵیوەشێنێتەوە.", show_alert=True)
        return

    context.user_data.pop("pending_signal", None)
    await query.answer()
    await query.edit_message_text("سیگناڵ هەڵوەشێندرایەوە.")


def main():
    setup_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("charts", charts))

    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^(member:|asset:|tf:)"))
    app.add_handler(CallbackQueryHandler(signal_handler, pattern=r"^signal:"))
    app.add_handler(CallbackQueryHandler(confirm_handler, pattern=r"^confirm_signal$"))
    app.add_handler(CallbackQueryHandler(cancel_handler, pattern=r"^cancel_signal$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, sl_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
