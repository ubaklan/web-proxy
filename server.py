from flask import Flask, request, jsonify
import requests
from http.client import HTTPConnection
import socket
import netifaces as ni
import threading


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

    try:
        print(f'Sending request to {url} with headers {headers} to interface {interface}')
        response = get_session(interface).get(url, headers=headers, allow_redirects=True)
        return jsonify(body=response.text)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/restart/<interface>', methods=['POST'])
def restart(interface):
    try:
        print(f'Sending reboot request to {interface}')
        threading.Thread(target=send_restart_request)
        return jsonify(status='async'), 200
    except Exception as e:
        return jsonify(error=str(e)), 500


def send_restart_request(interface):
    get_session(interface).post('http://192.168.100.1/ajax', json={'funcNo': '1013'})


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
    app.run(debug=True, host='0.0.0.0', port=3000)
