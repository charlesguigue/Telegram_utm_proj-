import os
import math
import re
import tempfile
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

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

def meters_to_lat(m):
    return m / 111_320

def meters_to_lon(m, lat):
    return m / (111_320 * math.cos(math.radians(lat)))

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

def create_square(lat, lon, size):
    dlat = meters_to_lat(size)
    dlon = meters_to_lon(size, lat)
    coords = [
        (lon - dlon, lat - dlat),
        (lon + dlon, lat - dlat),
        (lon + dlon, lat + dlat),
        (lon - dlon, lat + dlat),
    ]
    coords.append(coords[0])
    return coords

def create_hexagon(lat, lon, size):
    coords = []
    for i in range(6):
        angle = math.radians(60 * i)
        dlat = meters_to_lat(size) * math.sin(angle)
        dlon = meters_to_lon(size, lat) * math.cos(angle)
        coords.append((lon + dlon, lat + dlat))
    coords.append(coords[0])
    return coords

def create_diamond(lat, lon, size):
    dlat = meters_to_lat(size)
    dlon = meters_to_lon(size, lat)
    coords = [
        (lon, lat + dlat),
        (lon + dlon, lat),
        (lon, lat - dlat),
        (lon - dlon, lat),
    ]
    coords.append(coords[0])
    return coords

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

def generate_kml(points):
    kml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        '<Style id="shapeStyle">',
        '<LineStyle><color>A60000FF</color><width>2</width></LineStyle>',
        '<PolyStyle><color>A60000FF</color></PolyStyle>',
        '</Style>'
    ]

    for i, (name, (lat, lon)) in enumerate(points, start=1):
        coords = generate_shape(lat, lon)
        kml.append(f"""
        <Placemark>
            <name>{name}</name>
            <styleUrl>#shapeStyle</styleUrl>
            <Polygon>
                <outerBoundaryIs>
                    <LinearRing>
                        <coordinates>
                            {" ".join(f"{x},{y},0" for x, y in coords)}
                        </coordinates>
                    </LinearRing>
                </outerBoundaryIs>
            </Polygon>
        </Placemark>
        """)

    kml.append("</Document></kml>")
    return "\n".join(kml)

# ======================
# TELEGRAM HANDLER
# ======================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    matches = re.findall(r"([א-ת0-9 ]+)\s*-\s*(\d+[\/,]\d+)", text)

    if not matches:
        await update.message.reply_text("❌ Aucun point valide trouvé.")
        return

    points = []
    reply = []

    for idx, (name, m) in enumerate(matches, start=1):
        x, y = re.split("[/,]", m)
        lat = float(y) / 100000
        lon = float(x) / 100000
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
