#!/bin/bash
set -e
UNAME=$(uname -s)
if [ "$UNAME" = "Linux" ]
then
echo "Installing venv on Linux"
sudo apt update
sudo apt-get install -y python3-venv
fi
python3 -m venv .venv
. .venv/bin/activate
pip3 install -r requirements.txt