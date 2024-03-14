#!/bin/bash

source ~/web-proxy/venv/bin/activate
pip3 install -r ~/web-proxy/requirements.txt
python3 ~/web-proxy/server.py