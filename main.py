#!/usr/bin/env python3
# main.py - Advanced Production Telegram Bot (refactor)
import re
import utm
import logging
import os
from datetime import datetime
from simplekml import Kml
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
UTM_ZONE = int(os.getenv("UTM_ZONE", "36"))
UTM_LETTER = os.getenv("UTM_LETTER", "N")
LOG_FILE = os.getenv("LOG_FILE", "bot_log.txt")
# ==========================================

if not BOT_TOKEN:
    raise SystemExit("Missing BOT_TOKEN environment variable")

# -------- Logging --------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# File handler
fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Stream handler (stdout)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(formatter)
logger.addHandler(sh)

# -------- Parsing Functions --------

def parse_utm_slash(line):
    try:
        e, n = line.split("/")
        return float(e.strip()), float(n.strip())
    except Exception:
        return None


def parse_utm_space(line):
    try:
        parts = line.split()
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except Exception:
        return None


def parse_wgs84(line):
    try:
        if "," in line:
            lat, lon = line.split(",")
            return float(lat.strip()), float(lon.strip())
    except Exception:
        return None


def parse_google_maps(line):
    try:
        m = re.search(r"q=([-0-9.]+),([-0-9.]+)", line)
        if m:
            return float(m.group(1)), float(m.group(2))
    except Exception:
        return None


# -------- Conversion --------

def utm_to_latlon(easting, northing):
    return utm.to_latlon(easting, northing, UTM_ZONE, UTM_LETTER)


# -------- KML --------

def create_kml(points):
    kml = Kml()
    for name, lat, lon in points:
        kml.newpoint(name=name, coords=[(lon, lat)])

    filename = f"locations_{int(datetime.now().timestamp())}.kml"
    kml.save(filename)
    return filename


# -------- Notifications --------

async def notify_admin(context, message):
    try:
        if ADMIN_ID:
            await context.bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logging.error(f"Admin notification failed: {e}")


# -------- Main Handler --------

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    username = user.username if user.username else user.first_name
    user_id = user.id

    if not update.message or not update.message.text:
        return

    text = update.message.text
    lines = text.splitlines()

    logging.info(f"Message from {username} ({user_id})")

    results = []
    kml_points = []

    counter = 1

    try:

        for line in lines:

            line = line.strip()
            if not line:
                continue

            latlon = None

            utm_slash = parse_utm_slash(line)
            utm_space = parse_utm_space(line)
            wgs = parse_wgs84(line)
            gmaps = parse_google_maps(line)

            if utm_slash:
                latlon = utm_to_latlon(*utm_slash)

            elif utm_space:
                latlon = utm_to_latlon(*utm_space)

            elif wgs:
                latlon = wgs

            elif gmaps:
                latlon = gmaps

            if latlon:
                lat, lon = latlon
                link = f"https://www.google.com/maps?q={lat},{lon}"

                name = f"איתור {counter}"

                results.append(f"{name} -> {link}")
                kml_points.append((name, lat, lon))

                counter += 1

        if results:

            header = f"📍 Results for @{username}\n\n"
            await update.message.reply_text(header + "\n".join(results))

            kml_file = create_kml(kml_points)

            with open(kml_file, "rb") as f:
                await update.message.reply_document(f)

            os.remove(kml_file)

            await notify_admin(
                context,
                f"✅ Processed {len(results)} locations from @{username} ({user_id})"
            )

        else:
            await update.message.reply_text("לא נמצאו קואורדינטות תקינות")
            await notify_admin(
                context,
                f"⚠️ No valid coordinates from @{username} ({user_id})"
            )

    except Exception as e:
        logging.error(str(e))
        await update.message.reply_text("❌ שגיאה בעיבוד הנתונים")
        await notify_admin(
            context,
            f"❌ ERROR from @{username} ({user_id})\n{str(e)}"
        )


# -------- Bot Start --------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    logging.info("Bot Started")
    print("Bot Running...")

    app.run_polling()

if __name__ == "__main__":
    main()
