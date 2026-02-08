import os
import logging
import re
import math
import simplekml
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
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
def parse_utm(line):
    """Convert UTM coordinates to latitude and longitude."""
    m = re.search(r"(\d+\.?\d*)[\/,](\d+\.?\d*)", line)
    if not m:
        return None

    easting = float(m.group(1))
    northing = float(m.group(2))
    name = line.split('-')[0].strip() or "UTM"

    zone_number = 36  # Adjust this if necessary
    northern_hemisphere = True

    a = 6378137.0  # Equatorial radius in meters
    k0 = 0.9996
    e = 0.081819190842622

    n = northing if northern_hemisphere else northing - 10000000.0

    M = n / k0
    mu = M / (a * (1 - e**2 / 4 - 3 * e**4 / 64 - 5 * e**6 / 256))

    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))
    J1 = (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
    J2 = (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
    J3 = (151 * e1**3 / 96) * math.sin(6 * mu)
    J4 = (1097 * e1**4 / 512) * math.sin(8 * mu)
    lat = mu + J1 + J2 + J3 + J4

    C = e**2 * (math.cos(lat))**2 / (1 - e**2)
    Q = (easting - 500000) / (a * k0)
    lon = (zone_number * 6 - 183) + (Q / (1 - C)) * (1 / math.cos(lat))

    return lat * (180 / math.pi), lon * (180 / math.pi), name

def parse_wgs84(line):
    """Convert WGS84 coordinates to KML."""
    m = re.search(r"(-?\d+\.\d+),\s*(-?\d+\.\d+)", line)
    if not m:
        return None

    lat = float(m.group(1))
    lon = float(m.group(2))
    name = line.split('-')[0].strip() or "WGS84"

    return lat, lon, name

def create_kml(coords_list):
    """Create KML file with diamond shapes for given coordinates."""
    kml = simplekml.Kml()
    for lat, lon, name in coords_list:
        kml.newpoint(name=name, coords=[(lon, lat)])  # Add diamond shape
    kml_file = "coordinates.kml"
    kml.save(kml_file)
    return kml_file

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("UTM"), KeyboardButton("GWS84"), KeyboardButton("Google Maps")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "Welcome! Please choose an option below:",
        reply_markup=reply_markup
    )

async def handle_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text

    if user_choice == "UTM":
        await update.message.reply_text("Please send your UTM coordinates.")
    elif user_choice == "GWS84":
        await update.message.reply_text("Please send your WGS84 coordinates.")
    elif user_choice == "Google Maps":
        await update.message.reply_text("Please send your Google Maps link or address.")

async def handle_coordinates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.splitlines()
    results = []
    coords_list = []

    for line in lines:
        coords = parse_utm(line) or parse_wgs84(line)

        if not coords:
            results.append(f"❌ Invalid coordinates for: {line}")
            continue

        lat, lon, name = coords
        results.append(f"📍 {name} → [Google Maps link](https://www.google.com/maps?q={lat},{lon})")
        coords_list.append((lat, lon, name))

    # Create KML file if valid coordinates were found
    if coords_list:
        kml_file = create_kml(coords_list)
        results.append(f"KML file created: [Download here]({kml_file})")
    else:
        results.append("No valid coordinates found.")

    await update.message.reply_text("\n".join(results))

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_option))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^UTM$'), handle_coordinates))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex('^GWS84$'), handle_coordinates))

    logging.info("Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
