#!/bin/bash

source /home/vladimir/web-proxy/venv/bin/activate
pip3 install -r /home/vladimir/web-proxy/requirements.txt
touch /home/vladimir/web-proxy/hello.txt
python3 /home/vladimir/web-proxy/server.py