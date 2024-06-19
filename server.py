import socket
from http.client import HTTPConnection

import netifaces as ni
import requests
from flask import Flask, request, jsonify

BOT_TOKEN = '7033354884:AAEAmm4-ecOhwuVKTm6Q5d8qZsy_Px9DPZc'
DEFAULT_INTERFACE = 'wlan0'


def drop_accept_encoding_on_putheader(http_connection_putheader):
    def wrapper(self, header, *values):
        if header == "Accept-Encoding":
            return
        return http_connection_putheader(self, header, *values)

    return wrapper


HTTPConnection.putheader = drop_accept_encoding_on_putheader(HTTPConnection.putheader)


class HTTPAdapterWithSocketOptions(requests.adapters.HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.socket_options = kwargs.pop("socket_options", None)
        super(HTTPAdapterWithSocketOptions, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.socket_options is not None:
            kwargs["socket_options"] = self.socket_options
        super(HTTPAdapterWithSocketOptions, self).init_poolmanager(*args, **kwargs)


app = Flask(__name__)


@app.route('/proxy/<interface>', methods=['POST'])
def proxy(interface):
    url = request.json.get('url')
    headers = request.json.get('headers', {})
    requestCookie = headers.get('Cookie')
    print(f'Cookie from request header : {requestCookie}')
    headers['Cookie'] = '_pxhd=8316138300f521a89644af7ebf2c0785cc03b8f39c07d3b9908e9a4811fd9b27:45f353e4-120a-11ef-81d6-b2388b8b4315; pxcts=4860a7d4-120a-11ef-93c3-62238e9ac04b; _pxvid=45f353e4-120a-11ef-81d6-b2388b8b4315; salsify_session_id=3f01a419-8b50-4217-873b-258a4a20a16d; TS01a90220=012aaf475070a32d2d9057db193b3260381d7adf783786185fce39bb2b3b9b71452a158a3fb323e98c1d8fc9f3610a9ff6a1317ece;'
    updatedRequestCookie = headers.get('Cookie')
    print(f'Updated cookie from request header : {updatedRequestCookie}')
    try:
        print(f'Sending request to {url} with headers {headers} to interface {interface}')
        response = get_session(interface).get(url, headers=headers, allow_redirects=True, timeout=10)
        cookies = ''.join([str(x) + "=" + str(y) + "; " for x, y in zip(response.cookies.keys(), response.cookies.values())])
        return jsonify(headers=cookies, body=response.text)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/restart/<interface>', methods=['POST'])
def restart(interface):
    try:
        print(f'Sending reboot request to {interface}')
        response = get_session(interface).post('http://192.168.100.1/ajax', json={'funcNo': '1013'}, timeout=2)
        return jsonify(response=response), 200
    except requests.exceptions.Timeout:
        return jsonify(status='timeout, but expected :('), 200
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/interfaces', methods=['GET'])
def get_network_interfaces():
    interfaces = ni.interfaces()
    interface_info = []

    for interface in interfaces:
        addrs = ni.ifaddresses(interface)
        addr = addrs.get(ni.AF_LINK)[0]['addr'] if ni.AF_LINK in addrs else None

        if ni.AF_INET in addrs and addr is not None and is_interface_alive(interface):
            interface_info.append({"name": interface, "addr": addr})

    return jsonify(interfaces=interface_info)


@app.route('/update-gateway-ip', methods=['POST'])
def share_telegram_ip():
    public_ip = get_session(DEFAULT_INTERFACE).get('https://ifconfig.io/ip').text
    send_tg_message(public_ip)
    return '', 200


def send_tg_message(message):
    updates = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates')
    for result in updates.json()['result']:
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                                            json={'chat_id': result['message']['chat']['id'], 'text': message})


def is_interface_alive(interface):
    try:
        response = get_session(interface).head('https://google.com', timeout=0.5)
        return response.status_code < 400
    except Exception:
        return False


def get_session(interface):
    adapter = HTTPAdapterWithSocketOptions(socket_options=[(socket.SOL_SOCKET, 25, interface.encode('utf-8'))])
    session = requests.session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


if __name__ == '__main__':
    send_tg_message('Im alive!')
    share_telegram_ip()
    app.run(debug=True, host='0.0.0.0', port=3000)
