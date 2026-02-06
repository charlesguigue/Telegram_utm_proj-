import os
import logging
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import utm
import simplekml

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WHITELIST = {int(x.strip()) for x in os.getenv("WHITELIST_IDS", "").split(",") if x.strip().isdigit()}
UTM_ZONE = int(os.getenv("UTM_ZONE", 36))
UTM_LETTER = os.getenv("UTM_LETTER", "N")
LOG_FILE = os.getenv("LOG_FILE", "bot_log.txt")

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is missing or invalid. Check your environment variables!")

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)

# ---------------- HELPERS ----------------
def is_allowed(user_id: int) -> bool:
    return user_id in WHITELIST or user_id == ADMIN_ID

async def notify_admin(context, msg: str):
    if ADMIN_ID:
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

def parse_utm(part: str):
    """Parse a single UTM coordinate in the format easting/northing"""
    if "/" not in part:
        return None
    try:
        easting, northing = part.split("/")
        easting = float(easting)
        northing = float(northing)
        lat, lon = utm.to_latlon(easting, northing, UTM_ZONE, UTM_LETTER)
        return lat, lon
    except Exception:
        return None

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Access denied")
        return
    await update.message.reply_text(
        "📍 Send me UTM coordinates separated by spaces or slashes.\n"
        "Example: 709997/3505054 710090/3505147"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return
    try:
        text = update.message.text.strip()
        parts = re.split(r"[ \n]+", text)
        results = []
        kml = simplekml.Kml()
        count = 1

        for part in parts:
            coords = parse_utm(part)
            if coords:
                lat, lon = coords
                gmaps = f"https://maps.app.goo.gl/?q={lat},{lon}"
                results.append(f"📍 Location {count} -> {gmaps}")
                kml.newpoint(name=f"Location {count}", coords=[(lon, lat)])
                count += 1

        if not results:
            await update.message.reply_text("❌ No valid coordinates found. Please use easting/northing format (e.g., 709997/3505054).")
            return

        # Send list of links
        await update.message.reply_text("\n\n".join(results))

        # Save and send KML
        kml_path = "/tmp/locations.kml"
        kml.save(kml_path)
        await update.message.reply_document(open(kml_path, "rb"))

    except Exception as e:
        logging.exception("Error processing message")
        await update.message.reply_text("⚠️ Internal error occurred while processing your coordinates.")
        await notify_admin(context, f"❌ ERROR\nUser: @{user.username}\n{str(e)}")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("🤖 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
