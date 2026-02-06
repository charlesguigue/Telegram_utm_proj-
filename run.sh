#!/usr/bin/env bash
set -e

# Load env variables if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

exec python main.py
