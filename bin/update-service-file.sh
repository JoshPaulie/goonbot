#!/bin/bash

set +xe

sudo cp -v /home/pi/goonbot/bin/goonbot.service /etc/systemd/system

sudo systemctl daemon-reload
sudo systemctl restart goonbot
sudo systemctl status goonbot
