#!/bin/bash

# Ensure ran by root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

SERVICE_ACCOUNT="pi"
SERVICE_ACCOUNT_HOME="/home/$SERVICE_ACCOUNT"

install_python_3_12 () {
    echo "Installing Python 3.12.."

    # Update system
    sudo apt update && sudo apt upgrade -y

    # Download source
    wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz

    # Extract, cd into
    tar -xf Python-3.12.0.tgz
    cd Python-3.12.0 || { echo "Failed to cd into Python source dir, exiting."; exit 1; }

    # Compile
    ./configure --enable-optimizations
    make -j 4
    sudo make altinstall
}

# Make sure 3.12 is installed
# Python will always be installed on the Pi, but the version varies
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')

PINNED_PYTHON_VERSION="3.12"

if [[ "$PYTHON_VERSION" != "$PINNED_PYTHON_VERSION" && ! -f "/usr/local/bin/python3.12" ]]; then
    echo "Python ${PINNED_PYTHON_VERSION} is not installed."
    read -r -p "Would you like to install Python ${PINNED_PYTHON_VERSION}? y/n: " install
    case $install in
        [yY]* ) install_python_3_12 ;;
        [nN]* ) echo "We won't install Python at this time."; exit ;;
        *) exit ;;
    esac
else
    echo "Sufficient Python version installed: $PYTHON_VERSION" 
fi

# Clone repo to home
if [ -d "$SERVICE_ACCOUNT_HOME/goonbot" ]; then
    echo "Goonbot repo already exists."
else
    cd $SERVICE_ACCOUNT_HOME || { echo "Failed to cd into $SERVICE_ACCOUNT_HOME, exiting."; exit 1; }
    sudo -u $SERVICE_ACCOUNT git clone https://github.com/JoshPaulie/goonbot.git
fi

# Create venv and install requirements
cd $SERVICE_ACCOUNT_HOME/goonbot || { echo "Failed to cd into goonbot dir, exiting."; exit 1; }
sudo -u $SERVICE_ACCOUNT python3.12 -m venv .venv
sudo -u $SERVICE_ACCOUNT sh -c 'source .venv/bin/activate'
sudo -u $SERVICE_ACCOUNT pip install -r requirements.txt

# Copy service file to /etc/systemd/system, then start & enable it
SERVICE_FILE=/etc/systemd/system/goonbot.service
if [ -f "$SERVICE_FILE" ]; then
    echo "$SERVICE_FILE exists."
else 
    cp $SERVICE_ACCOUNT_HOME/goonbot/bin/goonbot.service /etc/systemd/system
    systemctl start goonbot
    systemctl enable goonbot
fi
