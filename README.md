# web-proxy

To create virtual env:
```
python3.9 -m venv venv
```

To activate virtual env:
```
source venv/bin/activate
```

Ubuntu setup:
```shell
sudo nano /etc/systemd/system/webproxy.service
```

Content:
```shell
[Unit]
Description=Web Proxy
After=network-online.target

[Service]
User=vladimir
WorkingDirectory=/home/vladimir/web-proxy
ExecStart=/home/vladimir/web-proxy/venv/bin/python3 /home/vladimir/web-proxy/server.py
Restart=always
RestartSec=15s
KillMode=process
User=vladimir

[Install]
WantedBy=multi-user.target
```

Start and test:
```shell
sudo systemctl daemon-reload
sudo systemctl enable webproxy.service
sudo systemctl start webproxy.service
sudo systemctl status webproxy.service
```

crontab-e
```shell
*/5 * * * * sleep 1m ; curl --location --request POST 'http://localhost:3000/restart/usb0' &
*/5 * * * * sleep 2m ; curl --location --request POST 'http://localhost:3000/restart/usb1' &
*/5 * * * * sleep 3m ; curl --location --request POST 'http://localhost:3000/restart/usb2' &
```