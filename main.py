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
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
    """Convert UTM coordinates to latitude and longitude."""
    match = re.match(r"^\s*(\d+)[/,](\d+)\s*$", part)
    if not match:
        return None
    try:
        easting = float(match.group(1))
        northing = float(match.group(2))
        lat, lon = utm.to_latlon(easting, northing, 36, 'N')  # Zone 36, North
        return lat, lon
    except Exception:
        return None

def create_diamond_kml(kml_obj, center_lat, center_lon, name="Loc"):
    """Create a diamond shape in a KML object."""
    dlat = 0.00003  # Approximate for 3m
    dlon = 0.00003

    points = [
        (center_lon, center_lat + dlat),  # Top
        (center_lon + dlon, center_lat),  # Right
        (center_lon, center_lat - dlat),  # Bottom
        (center_lon - dlon, center_lat)   # Left
    ]

    points.append(points[0])  # Close the diamond
    pol = kml_obj.newpolygon(name=name, outerboundaryis=points)
    pol.style.linestyle.color = simplekml.Color.red
    pol.style.linestyle.width = 2
    pol.style.polystyle.color = simplekml.Color.changealphaint(165, simplekml.Color.red)  # 65%
    pol.style.polystyle.fill = 1
    pol.style.polystyle.outline = 1

# ================= HANDLER =================
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
            name = f"Loc {count}"

            results.append(f"📍 {name} → {gmaps}")
            create_diamond_kml(kml, lat, lon, name)
            count += 1

        if not results:
            await update.message.reply_text("❌ No valid UTM coordinates found.")
            return

        await update.message.reply_text("\n".join(results))

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
