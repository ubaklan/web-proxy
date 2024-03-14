#!/bin/bash

cd /home/vladimir/web-proxy

source venv/bin/activate
pip3 install -r /home/vladimir/web-proxy/requirements.txt
#touch /home/vladimir/web-proxy/hello.txt
python3 server.py > log.log