#!/bin/bash
# Fly.io startup script for RG Assistant Bot

# Install ffmpeg if not present
if ! command -v ffmpeg &> /dev/null; then
    apt-get update && apt-get install -y ffmpeg
fi

# Run the bot
exec python -m main.telegram_server
