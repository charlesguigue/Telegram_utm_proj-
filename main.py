import os
import math
import re
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from pyproj import Proj, transform

# ======================
# CONFIG
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

KML_SHAPE = os.getenv("KML_SHAPE", "diamond").lower()
KML_SIZE_METERS = float(os.getenv("KML_SIZE_METERS", "3"))

if KML_SHAPE not in ["circle", "square", "hexagon", "diamond"]:
    KML_SHAPE = "diamond"

# ======================
# UTILS
# ======================

# Fonction pour convertir UTM à WGS84
def utm_to_wgs84(zone, easting, northing):
    proj_utm = Proj(proj="utm", zone=zone, ellps="WGS84")
    lon, lat = proj_utm(easting, northing, inverse=True)
    return lat, lon

# ======================
# SHAPES
# ======================

def create_circle(lat, lon, r_m, steps=36):
    coords = []
    for i in range(steps):
        angle = math.radians(i * (360 / steps))
        dlat = meters_to_lat(r_m) * math.sin(angle)
        dlon = meters_to_lon(r_m, lat) * math.cos(angle)
        coords.append((lon + dlon, lat + dlat))
    coords.append(coords[0])
    return coords

# Remaining shape generation functions...

def generate_shape(lat, lon):
    if KML_SHAPE == "circle":
        return create_circle(lat, lon, KML_SIZE_METERS)
    if KML_SHAPE == "square":
        return create_square(lat, lon, KML_SIZE_METERS)
    if KML_SHAPE == "hexagon":
        return create_hexagon(lat, lon, KML_SIZE_METERS)
    return create_diamond(lat, lon, KML_SIZE_METERS)

# ======================
# KML
# ======================

# KML generation function...

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    matches = re.findall(r"([א-ת0-9 ]+)\s*-\s*(\d+)\s*\/\s*(\d+)", text)

    if not matches:
        await update.message.reply_text("❌ Aucun point valide trouvé.")
        return

    points = []
    reply = []

    for idx, (name, easting, northing) in enumerate(matches, start=1):
        # Assume here the UTM zone as an example, you may need to adjust it based on your needs
        zone = 33  # Replace with appropriate UTM zone
        lat, lon = utm_to_wgs84(zone, float(easting), float(northing))
        points.append((name if name.strip() else f"Location {idx}", (lat, lon)))
        reply.append(f"📍 {name} -> https://www.google.com/maps?q={lat},{lon}")

    await update.message.reply_text("\n\n".join(reply))

    kml_content = generate_kml(points)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as f:
        f.write(kml_content.encode("utf-8"))
        path = f.name

    await update.message.reply_document(open(path, "rb"), filename="locations.kml")

# ======================
# MAIN
# ======================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN manquant")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot démarré et en cours d'exécution...")
    app.run_polling()

if __name__ == "__main__":
    main()
