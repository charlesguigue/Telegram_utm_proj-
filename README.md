# Advanced Production Telegram Bot

Bot Telegram simple prêt pour production (Docker + variables d'environnement).

## Lancement local
```bash
cp .env.example .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Lancement Docker
```bash
docker compose up -d --build
```
