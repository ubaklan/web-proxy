from flask import Flask, request, jsonify
import requests
from http.client import HTTPConnection
import socket
from dongle_lte_api import Dongle
import netifaces as ni

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
        adapter = HTTPAdapterWithSocketOptions(socket_options=[(socket.SOL_SOCKET, 25, interface.encode('utf-8'))])
        session = requests.session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        response = session.get(url, headers=headers, allow_redirects=True)
        return jsonify(body=response.text)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/restart/<interface>', methods=['POST'])
def restart(interface):
    ip = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
    info = Dongle(ip).get_data()
    print(info)
    return jsonify(body=info)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
