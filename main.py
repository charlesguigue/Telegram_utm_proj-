import os
import logging
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)
import utm
import simplekml

# ---------------- CONFIG ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WHITELIST = {
    int(x.strip())
    for x in os.getenv("WHITELIST_IDS", "").split(",")
    if x.strip().isdigit()
}

UTM_ZONE = int(os.getenv("UTM_ZONE", 36))
UTM_LETTER = os.getenv("UTM_LETTER", "N")
LOG_FILE = os.getenv("LOG_FILE", "bot_log.txt")

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


def parse_coordinates(text: str):
    text = text.strip()

    # Google Maps link
    gm = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", text)
    if gm:
        return float(gm.group(1)), float(gm.group(2))

    # Lat Lon
    ll = re.search(r"(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)", text)
    if ll:
        return float(ll.group(1)), float(ll.group(2))

    # UTM
    utm_match = re.search(r"(\d{6})\s+(\d{7})", text)
    if utm_match:
        easting = float(utm_match.group(1))
        northing = float(utm_match.group(2))
        lat, lon = utm.to_latlon(
            easting,
            northing,
            UTM_ZONE,
            UTM_LETTER
        )
        return lat, lon

    return None

# ---------------- HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Accès refusé")
        return

    await update.message.reply_text(
        "📍 Envoie-moi des coordonnées (UTM / LatLon / Google Maps)"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Utilisateur non autorisé")
        return

    try:
        coords = parse_coordinates(update.message.text)

        if not coords:
            await update.message.reply_text("❌ Coordonnées non reconnues")
            return

        lat, lon = coords
        gmaps = f"https://www.google.com/maps?q={lat},{lon}"

        # KML
        kml = simplekml.Kml()
        kml.newpoint(name="Point", coords=[(lon, lat)])
        kml_path = "/tmp/location.kml"
        kml.save(kml_path)

        await update.message.reply_text(f"📍 {lat}, {lon}\n🌍 {gmaps}")
        await update.message.reply_document(open(kml_path, "rb"))

    except Exception as e:
        logging.exception("Erreur traitement message")
        await update.message.reply_text("⚠️ Erreur interne")
        await notify_admin(
            context,
            f"❌ ERREUR\nUser: @{user.username}\n{str(e)}"
        )


# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("🤖 Bot démarré")
    app.run_polling()


if __name__ == "__main__":
    main()
