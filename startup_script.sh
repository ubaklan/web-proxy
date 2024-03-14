#!/bin/bash

source ~/web-proxy/venv/bin/activate
pip3 install -r ~/web-proxy/requirements.txt
touch ~/web-proxy/hello.txt
python3 ~/web-proxy/server.py