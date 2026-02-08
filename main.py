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
import re
import math

def parse_utm(line):
    m = re.match(r"\s*(\d+\.?\d*),\s*(\d+\.?\d*);?([^\s]+)?\s*$", line)
    if not m:
        return None

    easting = float(m.group(1))
    northing = float(m.group(2))
    name = m.group(3) or "UTM"

    # Zone UTM pour Israël, Zone 36N
    zone_number = 36
    northern_hemisphere = True  # Assurez-vous que cela est correct pour vos données

    # Calcul des coordonnées latitude/longitude à partir des coordonnées UTM
    # Équations basées sur la projection UTM
    a = 6378137.0  # Rayon équatorial en mètres
    k0 = 0.9996    # Facteur d'échelle
    e = 0.081819190842622  # Première excentricité

    # Calcul zone, il peut être nécessaire de régler selon la zone
    if northern_hemisphere:
        n = northing
    else:
        n = northing - 10000000.0  # Ajuster pour l'hémisphère sud

    # Calcul de latitude
    M = n / k0
    mu = M / (a * (1 - e**2 / 4 - 3 * e**4 / 64 - 5 * e**6 / 256))

    # Calcul de latitude et longitude
    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))  # Premier facteur d'excentricité
    J1 = (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
    J2 = (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
    J3 = (151 * e1**3 / 96) * math.sin(6 * mu)
    J4 = (1097 * e1**4 / 512) * math.sin(8 * mu)
    lat = mu + J1 + J2 + J3 + J4

    # Calcul longitude
    C = e**2 * (math.cos(lat))**2 / (1 - e**2)
    T = (math.tan(lat))**2
    Q = (easting - 500000) / (a * k0)
    lon = (zone_number * 6 - 183) + (Q / (1 - C)) * (1 / math.cos(lat))

    return lat * (180 / math.pi), lon * (180 / math.pi), name  # Conversion radians à degrés

def create_circle_kml(kml_obj, center_lat, center_lon, radius_m=3, name="Loc"):
    points = []
    num_points = 72  # smooth circle

    for i in range(num_points + 1):  # +1 to close polygon
        angle = math.radians(i * (360 / num_points))
        delta_lat = (radius_m / 111320) * math.cos(angle)
        delta_lon = (radius_m / (111320 * math.cos(math.radians(center_lat)))) * math.sin(angle)

        lat = center_lat + delta_lat
        lon = center_lon + delta_lon
        points.append((lon, lat))

    pol = kml_obj.newpolygon(
        name=name,
        outerboundaryis=points,
    )

    pol.style.linestyle.color = simplekml.Color.red
    pol.style.linestyle.width = 2
    pol.style.polystyle.color = simplekml.Color.changealphaint(165, simplekml.Color.red)  # 65%
    pol.style.polystyle.fill = 1
    pol.style.polystyle.outline = 1

def create_diamond_kml(kml_obj, center_lat, center_lon, size_m=3, name="Diamond"):
    dlat = size_m / 111320
    dlon = size_m / (111320 * math.cos(math.radians(center_lat)))

    # Coordinates for the diamond
    points = [
        (center_lon, center_lat + dlat),       # Top
        (center_lon + dlon, center_lat),       # Right
        (center_lon, center_lat - dlat),       # Bottom
        (center_lon - dlon, center_lat),       # Left
    ]
    points.append(points[0])  # Close the diamond

    pol = kml_obj.newpolygon(
        name=name,
        outerboundaryis=points,
    )

    pol.style.linestyle.color = simplekml.Color.blue
    pol.style.linestyle.width = 2
    pol.style.polystyle.color = simplekml.Color.changealphaint(165, simplekml.Color.blue)  # 65%
    pol.style.polystyle.fill = 1
    pol.style.polystyle.outline = 1

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📍 Envoyez des coordonnées UTM.\n\n"
        "Formats supportés:\n"
        "709997/3505054\n"
        "709997,3505054\n\n"
        "Vous pouvez envoyer plusieurs coordonnées séparées par des espaces ou des lignes."
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
            gmaps = f"https://www.google.com/maps?q={lat},{lon}"
            name = f"Loc {count}"  # Nom par défaut

            results.append(f"📍 {name} → {gmaps}")
            create_circle_kml(kml, lat, lon, radius_m=3, name=name)
            create_diamond_kml(kml, lat, lon, size_m=3, name=f"Diamond {count}")
            count += 1

        if not results:
            await update.message.reply_text(
                "❌ Aucun point UTM valide trouvé.\n"
                "Utilisez easting/northing avec / ou ,"
            )
            return

        await update.message.reply_text("\n\n".join(results))

        kml_path = "/tmp/locations.kml"
        kml.save(kml_path)
        await update.message.reply_document(open(kml_path, "rb"))

    except Exception as e:
        logging.exception("Erreur de traitement")
        await update.message.reply_text(
            "⚠️ Une erreur interne est survenue lors du traitement de votre message."
        )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Bot démarré avec succès")
    app.run_polling()

if __name__ == "__main__":
    main()
