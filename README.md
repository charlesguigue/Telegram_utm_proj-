# Advanced Production Telegram Bot

Bot Telegram qui parse des coordonnées (UTM / WGS84 / Google Maps), renvoie des liens Google Maps, génère un KML et notifie un administrateur.

Prérequis
- Python 3.10+
- Docker (optionnel)
- Un token de bot Telegram (BOT_TOKEN)
- Ton ID Telegram en tant qu'administrateur (ADMIN_ID)

Fichiers fournis
- main.py : code du bot
- requirements.txt : dépendances Python
- Dockerfile : image Docker pour exécution
- docker-compose.yml : exécution locale avec restart
- .env.example : variables d'environnement à renseigner
- run.sh : script de lancement local
- .github/workflows/ci.yml : exemple de workflow GitHub Actions pour builder l'image

Installation locale (virtuelenv)
1. Copier `.env.example` en `.env` et renseigner BOT_TOKEN et ADMIN_ID.
2. python -m venv venv
3. source venv/bin/activate
4. pip install -r requirements.txt
5. export $(cat .env | xargs)   # ou utiliser direnv
6. python main.py

Exécution en Docker
1. Copier `.env.example` en `.env` et renseigner les valeurs.
2. docker compose up -d --build
Le service est configuré pour redémarrer automatiquement.

Déploiement
- Tu peux utiliser GitHub Actions pour builder et pousser l'image sur un registry, puis déployer sur ton serveur (exemple inclus dans `.github/workflows/ci.yml`).

Sécurité
- Ne pousse jamais `.env` contenant BOT_TOKEN sur un repo public.
