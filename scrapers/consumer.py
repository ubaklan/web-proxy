import socket

import netifaces as ni
import requests
import threading


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


def process_categories(iface, iface_categories):
    thread_name = threading.current_thread().name
    thread_id = threading.get_native_id()

    print(f"Thread Name: {thread_name}, Thread ID: {thread_id}")
    print(iface)
    print(iface_categories)

    threads = []

    for category in iface_categories:
        thread = threading.Thread(
            target=scrape_category,
            args=(interface, category)
        )
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def scrape_category(iface, category_url):
    print('Scraping ' + category_url + ',' + iface['name'])

if __name__ == '__main__':
    all_categories = read_file_to_array('resources/categories.csv')

    categories = all_categories[:10]
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
            args=(interface, categories_for_interface),
            name=f"Thread-{i + 1}"
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
    print("All threads have completed.")
