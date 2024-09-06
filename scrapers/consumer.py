import aiohttp
import asyncio
import netifaces as ni
import socket
import random
from bs4 import BeautifulSoup
import json
import time


def timing_decorator(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
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


async def get_session(interface):
    # aiohttp doesn’t use socket_options, so this is a simplified version
    session = aiohttp.ClientSession()
    return session


async def get_category_page_content(session, category_url, user_agent):
    headers = {
        'User-Agent': user_agent,
        'Content-Type': 'text/plain;text/html',
        'Accept': 'text/html,application/xhtml+xml,'
                  'application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.7'
    }
    async with session.get(category_url, headers=headers, allow_redirects=True, timeout=120) as response:
        return await response.text()


async def parse(raw_content):
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


async def save_category(payload):
    headers = {
        'x-api-key': 'b9e0cfc7-9ba4-43b9-b38f-3191d1f8d686',
        'Content-Type': 'application/json'
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post('https://core-data-api.threecolts.com/raw-walmart/categories', headers=headers,
                                    json=payload, timeout=360) as response:
                response.raise_for_status()
                print('Sent categories to API: ' + str(response.status))
        except aiohttp.ClientResponseError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Other error occurred: {err}")


async def restart(interface):
    try:
        print(f'Sending reboot request to {interface}')
        async with aiohttp.ClientSession() as session:
            async with session.post('http://192.168.100.1/ajax', json={'funcNo': '1013'}, timeout=2) as response:
                await response.text()  # Make sure the request is completed
    except aiohttp.ClientTimeout:
        print('timeout, but expected :(')
    except Exception as e:
        print(str(e))


async def process_categories(session, iface, iface_categories, user_agents):
    tasks = []

    for category in iface_categories:
        user_agent = random.choice(user_agents)
        task = get_category_page_content(session, category, user_agent)
        tasks.append(task)

    raw_contents = await asyncio.gather(*tasks)
    return raw_contents


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
    print(interfaces)
    interface_info = []
    for interface in interfaces:
        addrs = ni.ifaddresses(interface)
        addr = addrs.get(ni.AF_LINK)[0]['addr'] if ni.AF_LINK in addrs else None
        if ni.AF_INET in addrs and addr is not None and interface != 'wlan0' and is_interface_alive(interface):
            interface_info.append({"name": interface, "addr": addr})
    return interface_info


def split_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


async def process_top_level_categories(categories, user_agents):
    interfaces = get_network_interfaces()
    interfaces_len = len(interfaces)
    print('INTERFACES: ' + str(interfaces_len))
    partitioned_categories = split_list(categories, interfaces_len)
    all_raw_contents = []

    async with aiohttp.ClientSession() as session:
        # Process categories asynchronously
        tasks = [
            process_categories(session, iface, categories_for_interface, user_agents)
            for iface, categories_for_interface in zip(interfaces, partitioned_categories)
        ]
        results = await asyncio.gather(*tasks)

        for raw_contents in results:
            all_raw_contents.extend(raw_contents)

        # Restart interfaces
        restart_tasks = [restart(iface['name']) for iface in interfaces]
        await asyncio.gather(*restart_tasks)

    # Record start time for waiting
    start_time = time.time()

    # Parse and send results to API
    parse_tasks = [parse(raw_content) for raw_content in all_raw_contents]
    parsed_results = await asyncio.gather(*parse_tasks)

    # Filter out None results and send them to the API
    save_tasks = [save_category(result.raw_json) for result in parsed_results if result]
    await asyncio.gather(*save_tasks)

    # Calculate remaining time to wait after processing
    end_time = time.time()
    elapsed_time = end_time - start_time
    waiting_time = max(120 - elapsed_time, 0)  # Ensure non-negative waiting time

    print(f"Going to wait for {waiting_time} sec.")
    await asyncio.sleep(waiting_time)
    print("All threads have completed.")


if __name__ == '__main__':
    top_level_all_categories = read_file_to_array('resources/categories.csv')
    top_level_user_agents = read_file_to_array('resources/user_agents.csv')


    async def main():
        for top_level_categories in split_list(top_level_all_categories, 200):
            await process_top_level_categories(top_level_categories, top_level_user_agents)


    asyncio.run(main())
