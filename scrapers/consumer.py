import socket

import netifaces as ni
import requests
import threading
import random

from bs4 import BeautifulSoup
import json
import time
import asyncio


class CategoryPageParseResult:
    def __init__(self, raw_json, max_page, current_page):
        self.raw_json = raw_json
        self.max_page = max_page
        self.current_page = current_page


class HTTPAdapterWithSocketOptions(requests.adapters.HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.socket_options = kwargs.pop("socket_options", None)
        super(HTTPAdapterWithSocketOptions, self).__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        if self.socket_options is not None:
            kwargs["socket_options"] = self.socket_options
        super(HTTPAdapterWithSocketOptions, self).init_poolmanager(*args, **kwargs)


def read_file_to_array(filename):
    lines = []
    with open(filename, 'r') as file:
        for line in file:
            lines.append(line.strip())  # strip() removes newline and extra spaces
    return lines


def is_interface_alive(interface):
    try:
        response = get_session(interface).head('https://google.com', timeout=0.5)
        return response.status_code < 400
    except Exception:
        return False


def get_network_interfaces():
    interfaces = ni.interfaces()
    interface_info = []

    for interface in interfaces:
        addrs = ni.ifaddresses(interface)
        addr = addrs.get(ni.AF_LINK)[0]['addr'] if ni.AF_LINK in addrs else None

        if ni.AF_INET in addrs and addr is not None and interface != 'wlan0' and is_interface_alive(interface):
            interface_info.append({"name": interface, "addr": addr})

    return interface_info


def get_session(interface):
    adapter = HTTPAdapterWithSocketOptions(socket_options=[(socket.SOL_SOCKET, 25, interface.encode('utf-8'))])
    session = requests.session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def split_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def process_categories(iface, iface_categories, user_agents):
    thread_name = threading.current_thread().name
    thread_id = threading.get_native_id()

    print(f"Thread Name: {thread_name}, Thread ID: {thread_id}")
    print(iface)
    print(iface_categories)

    threads = []

    for category in iface_categories:
        thread = threading.Thread(
            target=scrape_category,
            args=(iface, category, random.choice(user_agents))
        )
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def scrape_category(iface, category_url, user_agent):
    print('Scraping ' + category_url + ',' + iface['name'] + ',' + user_agent)
    headers = {
        'User-Agent': user_agent,
        'Content-Type': 'text/plain;text/html',
        'Accept': 'text/html,application/xhtml+xml,'
                  'application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.7'
    }

    response = get_session(iface['name']).get(category_url, headers=headers, allow_redirects=True, timeout=120)
    parsed = parse(response.text)
    save_category(parsed.raw_json)


def parse(raw_content):
    try:
        soup = BeautifulSoup(raw_content, 'html.parser')
        data = soup.find(id="__NEXT_DATA__").string
        raw_json = json.loads(data)

        pagination_v2 = raw_json['props']['pageProps']['initialData']['searchResult']['paginationV2']

        max_page = pagination_v2['maxPage']
        current_page = pagination_v2['pageProperties']['page']

        return CategoryPageParseResult(
            raw_json=json.dumps(raw_json),
            max_page=max_page,
            current_page=current_page
        )
    except Exception as e:
        print(f"Exception caught: {e}")
        return None


def save_category(payload):
    headers = {
        'x-api-key': 'b9e0cfc7-9ba4-43b9-b38f-3191d1f8d686',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post('https://core-data-api.threecolts.com/raw-walmart/categories', headers=headers,
                                 data=payload, timeout=360)
        response.raise_for_status()
        print('Sent categories to API: ' + str(response.status_code))
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
    return None


def restart(interface):
    try:
        print(f'Sending reboot request to {interface}')
        response = get_session(interface).post('http://192.168.100.1/ajax', json={'funcNo': '1013'}, timeout=2)
    except requests.exceptions.Timeout:
        print('timeout, but expected :(')
    except Exception as e:
        print(str(e))


if __name__ == '__main__':
    all_categories = read_file_to_array('resources/categories.csv')
    user_agents = read_file_to_array('resources/user_agents.csv')

    for categories in split_list(all_categories, 200):
        interfaces = get_network_interfaces()
        interfaces_len = len(interfaces)

        print('INTERFACES: ' + str(interfaces_len))
        partitioned_categories = split_list(categories, interfaces_len)

        threads = []

        for i in range(interfaces_len):
            interface = interfaces[i]
            categories_for_interface = partitioned_categories[i]
            thread = threading.Thread(
                target=process_categories,
                args=(interface, categories_for_interface, user_agents),
                name=f"Thread-{i + 1}"
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        for iface in interfaces:
            restart(iface['name'])

        print("Going to wait for 120 sec.")
        time.sleep(120)
        print("All threads have completed.")
