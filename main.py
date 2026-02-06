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
UTM_ZONE = int(os.getenv("UTM_ZONE", "36"))
UTM_LETTER = os.getenv("UTM_LETTER", "N")
LOG_FILE = os.getenv("LOG_FILE", "bot_log.txt")
KML_SHAPE = os.getenv("KML_SHAPE", "diamond").lower()  # circle | square | hexagon | diamond

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


def meters_to_deg_lat(m):
    return m / 111320


def meters_to_deg_lon(m, lat):
    return m / (111320 * math.cos(math.radians(lat)))


def create_shape_kml(kml, lat, lon, radius_m, name):
    shape = KML_SHAPE
    points = []

    # Définition des formes
    if shape == "circle":
        sides = 72
        angles = [i * (360 / sides) for i in range(sides + 1)]

    elif shape == "hexagon":
        angles = [i * 60 for i in range(7)]

    elif shape == "square":
        angles = [45, 135, 225, 315, 45]

    elif shape == "diamond":
        angles = [0, 90, 180, 270, 0]

    else:
        angles = [i * (360 / 72) for i in range(73)]

    # Construction du polygone
    for angle in angles:
        rad = math.radians(angle)
        dlat = meters_to_deg_lat(radius_m) * math.cos(rad)
        dlon = meters_to_deg_lon(radius_m, lat) * math.sin(rad)
        points.append((lon + dlon, lat + dlat))

    pol = kml.newpolygon(
        name=name,
        outerboundaryis=points,
    )

    # Style
    pol.style.linestyle.color = simplekml.Color.red
    pol.style.linestyle.width = 2
    pol.style.polystyle.color = simplekml.Color.changealphaint(
        165, simplekml.Color.red
    )
    pol.style.polystyle.fill = 1
    pol.style.polystyle.outline = 1


# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 Send UTM coordinates.\n\n"
        "Formats:\n"
        "709997/3505054\n"
        "709997,3505054\n\n"
        "Multiple coordinates supported."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = re.split(r"[ \n]+", update.message.text.strip())
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

            create_shape_kml(
                kml,
                lat,
                lon,
                radius_m=3,
                name=f"Loc {count}",
            )
            count += 1

        if not results:
            await update.message.reply_text(
                "❌ No valid UTM coordinates found."
            )
            return

        await update.message.reply_text("\n\n".join(results))

        path = "/tmp/locations.kml"
        kml.save(path)
        await update.message.reply_document(open(path, "rb"))

    except Exception:
        logging.exception("Processing error")
        await update.message.reply_text(
            "⚠️ Internal error occurred."
        )


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info(f"Bot started | KML shape = {KML_SHAPE}")
    app.run_polling()


if __name__ == "__main__":
    main()
