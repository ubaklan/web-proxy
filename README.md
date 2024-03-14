# web-proxy

To create virtual env:
```
python3 -m venv venv
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
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/vladimir/web-proxy
ExecStart=venv/bin/python3 server.py
Restart=always

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