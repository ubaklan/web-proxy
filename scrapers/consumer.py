import socket
import netifaces as ni
import requests
import threading
import random
from bs4 import BeautifulSoup
import json
import time


def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time for {func.__name__}: {execution_time:.4f} seconds")
        return result

    return wrapper


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
    return list(lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


def split_into_chunks(array, chunk_size=300):
    # Create a list to hold the chunks
    chunks = []

    # Iterate over the array and split it into chunks
    for i in range(0, len(array), chunk_size):
        chunk = array[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


def process_categories(iface, iface_categories, user_agents):
    threads = []
    raw_contents = []

    def thread_target(_category, user_agent):
        response = get_category_page_content(iface, _category, user_agent)
        raw_contents.append(response.text)

    for category in iface_categories:
        thread = threading.Thread(
            target=thread_target,
            args=(category, random.choice(user_agents))
        )
        threads.append(thread)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return raw_contents


def get_category_page_content(iface, category_url, user_agent):
    headers = {
        'User-Agent': user_agent,
        'Content-Type': 'text/plain;text/html',
        'Accept': 'text/html,application/xhtml+xml,'
                  'application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.7'
    }
    print('Making a request to category: ' + category_url + ',' + iface['name'])
    result = get_session(iface['name']).get(category_url, headers=headers, allow_redirects=True, timeout=60)
    print('Got response from walmart')
    return result


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


def save_category(raw_content):
    payload = parse(raw_content)
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


def process_top_level_categories(categories, user_agents):
    interfaces = get_network_interfaces()
    interfaces_len = len(interfaces)
    print('INTERFACES: ' + str(interfaces_len))
    print('Categories len: ' + str(len(categories)))
    partitioned_categories = split_list(categories, interfaces_len)
    print('Partitioned categories len: ' + str(len(categories)))
    all_raw_contents = []

    categories_threads = []

    def thread_target(_iface, iface_categories):
        response = process_categories(_iface, iface_categories, user_agents)
        all_raw_contents.extend(response)

    # Process categories
    for i in range(interfaces_len):
        interface = interfaces[i]
        categories_for_interface = partitioned_categories[i]
        print('Categories for interface: ' + str(len(categories_for_interface)))
        thread = threading.Thread(
            target=thread_target,
            args=(interface, categories_for_interface)
        )
        categories_threads.append(thread)
        thread.start()

    for thread in categories_threads:
        thread.join()

    # Restart interfaces
    for iface in interfaces:
        restart(iface['name'])

    # Record start time for waiting
    start_time = time.time()

    save_data_api_threads = []

    # Parse and send results to API
    for raw_content in all_raw_contents:
        thread = threading.Thread(
            target=save_category,
            args=(raw_content,)
        )

        save_data_api_threads.append(thread)

    for thread in save_data_api_threads:
        thread.start()

    for thread in save_data_api_threads:
        thread.join()

    # Calculate remaining time to wait after processing
    end_time = time.time()
    elapsed_time = end_time - start_time
    waiting_time = max(120 - elapsed_time, 0)  # Ensure non-negative waiting time

    print(f"Going to wait for {waiting_time} sec.")
    time.sleep(waiting_time)
    print("All threads have completed.")


if __name__ == '__main__':
    top_level_all_categories = read_file_to_array('resources/categories.csv')
    top_level_user_agents = read_file_to_array('resources/user_agents.csv')

    for top_level_categories in split_into_chunks(top_level_all_categories, 150):
        process_top_level_categories(top_level_categories, top_level_user_agents)
