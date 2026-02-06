#!/usr/bin/env bash
# Simple startup script to run the bot
set -e

# Load env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

exec python main.py
