#!/bin/bash

install_py () {
    echo "Bootstrapping Python 3.12.."

    # Update system
    sudo apt update && sudo apt upgrade -y

    # Download source
    wget https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz

    # Extract, cd into
    tar -xf Python-3.12.0.tgz
    cd Python-3.12.0

    # Compile
    ./configure --enable-optimizations
    make -j 4
    sudo make altinstall
}

# Make sure 3.12 is installed
# Python will always be installed on the Pi, but the version varies
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')

MINIMUM_PYTHON_VERSION="3.12"

if [[ "$PYTHON_VERSION" < "$MINIMUM_PYTHON_VERSION" ]]; then
    echo "Python version is below the minimum of ${MINIMUM_PYTHON_VERSION}."
    read -r -p "Would you like to install Python ${MINIMUM_PYTHON_VERSION}? y/n: " install
    case $install in
        [yY]* ) install_py ;;
        [nN]* ) echo "We won't install Python at this time."; exit ;;
        *) exit ;;
    esac
else
    echo "Sufficient Python version installed: $PYTHON_VERSION" 
fi

# Copy service file to /etc/systemd/system
SERVICEFILE=/etc/systemd/system/Goonbot.service
if [ -f "$SERVICEFILE" ]; then
    echo "$SERVICEFILE exists."
else 
    cp /home/pi/goonbot/bin/Goonbot.service /etc/systemd/system
fi