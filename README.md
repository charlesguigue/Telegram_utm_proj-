# Telegram Bot Production

Bot Telegram qui parse des coordonnées UTM / LatLon / Google Maps, génère un KML et notifie un admin.

## Installation

1. Copier `.env.example` → `.env` et remplir BOT_TOKEN, ADMIN_ID
2. `docker compose up -d --build`

Le bot redémarrera automatiquement en cas de crash.
