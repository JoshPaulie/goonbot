#!/bin/bash

# Very simply start script for the bot

# Project dir
cd /home/pi/goonbot
# Update project
git pull
# Clear screen of git clutter
clear
echo "Bot is up to date."
# Start bot
source .venv/bin/activate
python main.py