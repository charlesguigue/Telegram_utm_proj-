#!/usr/bin/env bash
set -e
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
exec python main.py
