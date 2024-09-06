# web-proxy

To create virtual env:
```
python3.9 -m venv venv
```

To activate virtual env:
```
source venv/bin/activate
```

# Webproxy service setup:
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

# Reverse tunnel setup:
```shell
sudo nano /etc/systemd/system/reverse-ssh-tunnel.service
```

Content:
```shell
[Unit]
Description=Reverse SSH Tunnel to VPS
After=network-online.target

[Service]
ExecStart=/usr/bin/ssh -N -R 0.0.0.0:3000:localhost:3000 ubuntu@ec2-54-84-105-236.compute-1.amazonaws.com -i /home/vladimir/web-proxy/uladzimir-check-ssh-dir.pem
Restart=always
User=vladimir
RestartSec=30s
KillMode=process

[Install]
WantedBy=multi-user.target
```

Start and test:
```shell
sudo systemctl daemon-reload
sudo systemctl enable reverse-ssh-tunnel
sudo systemctl start reverse-ssh-tunnel
sudo systemctl status reverse-ssh-tunnel
```

Proxy VPS:
```
sudo nano /etc/ssh/sshd_config
Add - GatewayPorts yes
sudo systemctl restart ssh

```

crontab-e
```shell
*/5 * * * * sleep 1m ; curl --location --request POST 'http://localhost:3000/restart/usb0' &
*/5 * * * * sleep 2m ; curl --location --request POST 'http://localhost:3000/restart/usb1' &
*/5 * * * * sleep 3m ; curl --location --request POST 'http://localhost:3000/restart/usb2' &
```
