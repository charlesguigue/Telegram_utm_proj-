from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from config import TOKEN, DEFAULT_COLOR, VISIBILITY_PERCENT
from parsers import parse_google_maps, parse_wgs84, parse_utm
from kml import polygon_kml, fallback_polygon, get_color_with_transparency

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📍 שלח קואורדינטות")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.splitlines()
    context.user_data["items"] = []

    current_name = None
    for line in lines:
        if not line.startswith("http"):
            current_name = line.strip()
            continue

        parsed = parse_google_maps(line)
        if parsed:
            context.user_data["items"].append((*parsed, current_name))
            continue

        parsed = parse_wgs84(line)
        if parsed:
            context.user_data["items"].append(parsed)
            continue

        parsed = parse_utm(line, current_name)
        if parsed:
            context.user_data["items"].append(parsed)

    if context.user_data["items"]:
        keyboard = [[InlineKeyboardButton("✅ ייצור KML", callback_data="kml")]]
        await update.message.reply_text("מוכן לייצוא", reply_markup=InlineKeyboardMarkup(keyboard))

async def generate_kml(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    color = get_color_with_transparency(DEFAULT_COLOR, VISIBILITY_PERCENT)

    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
"""
    for lat, lon, name in context.user_data["items"]:
        kml += polygon_kml(
            fallback_polygon(lat, lon),
            name,
            "Generated polygon",
            color
        )

    kml += "</Document></kml>"

    with open("buildings.kml", "w", encoding="utf-8") as f:
        f.write(kml)

    await q.message.reply_document(open("buildings.kml", "rb"))

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(generate_kml, pattern="kml"))
    app.run_polling()

if __name__ == "__main__":
    main()
