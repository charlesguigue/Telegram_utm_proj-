import os
import logging
import re
import math
import utm
import simplekml
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
UTM_ZONE = int(os.getenv("UTM_ZONE", "36"))
UTM_LETTER = os.getenv("UTM_LETTER", "N")
LOG_FILE = os.getenv("LOG_FILE", "bot_log.txt")

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing or invalid")

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ],
)

# ================= HELPERS =================
def parse_utm(part: str):
    """
    Accepts:
    - 709997/3505054
    - 709997,3505054
    """
    match = re.match(r"^\s*(\d+(?:\.\d+)?)[/,](\d+(?:\.\d+)?)\s*$", part)
    if not match:
        return None
    try:
        easting = float(match.group(1))
        northing = float(match.group(2))
        lat, lon = utm.to_latlon(easting, northing, UTM_ZONE, UTM_LETTER)
        return lat, lon
    except Exception:
        return None


def create_circle_kml(kml_obj, center_lat, center_lon, radius_m=3, name="Loc"):
    points = []
    num_points = 72  # smooth circle

    for i in range(num_points + 1):  # +1 to close polygon
        angle = math.radians(i * (360 / num_points))

        delta_lat = (radius_m / 111320) * math.cos(angle)
        delta_lon = (
            radius_m / (111320 * math.cos(math.radians(center_lat)))
        ) * math.sin(angle)

        lat = center_lat + delta_lat
        lon = center_lon + delta_lon
        points.append((lon, lat))

    pol = kml_obj.newpolygon(
        name=name,
        outerboundaryis=points,
    )

    pol.style.linestyle.color = simplekml.Color.red
    pol.style.linestyle.width = 2
    pol.style.polystyle.color = simplekml.Color.changealphaint(
        165, simplekml.Color.red
    )  # 65%
    pol.style.polystyle.fill = 1
    pol.style.polystyle.outline = 1


# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 Send UTM coordinates.\n\n"
        "Supported formats:\n"
        "709997/3505054\n"
        "709997,3505054\n\n"
        "You can send multiple coordinates separated by spaces or lines."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        parts = re.split(r"[ \n]+", text)

        kml = simplekml.Kml()
        results = []
        count = 1

        for part in parts:
            coords = parse_utm(part)
            if not coords:
                continue

            lat, lon = coords
            gmaps = f"https://maps.app.goo.gl/?q={lat},{lon}"

            results.append(f"📍 Loc {count} → {gmaps}")
            create_circle_kml(
                kml,
                lat,
                lon,
                radius_m=3,
                name=f"Loc {count}",
            )
            count += 1

        if not results:
            await update.message.reply_text(
                "❌ No valid UTM coordinates found.\n"
                "Use easting/northing with / or ,"
            )
            return

        await update.message.reply_text("\n\n".join(results))

        kml_path = "/tmp/locations.kml"
        kml.save(kml_path)
        await update.message.reply_document(open(kml_path, "rb"))

    except Exception as e:
        logging.exception("Processing error")
        await update.message.reply_text(
            "⚠️ An internal error occurred while processing your message."
        )


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Bot started successfully")
    app.run_polling()


if __name__ == "__main__":
    main()

