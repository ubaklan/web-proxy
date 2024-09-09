import time

import requests
import random
from bs4 import BeautifulSoup
import json


class CategoryPageParseResult:
    def __init__(self, raw_json, max_page, current_page):
        self.raw_json = raw_json
        self.max_page = max_page
        self.current_page = current_page


def get_category_page_content(category_url, user_agent):
    headers = {
        'User-Agent': user_agent,
        'Content-Type': 'text/plain;text/html',
        'Accept': 'text/html,application/xhtml+xml,'
                  'application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.7'
    }
    print('Making a request to category: ' + category_url)
    result = requests.get(category_url, headers=headers, allow_redirects=True, timeout=60)
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
                                 data=payload.raw_json, timeout=360)
        response.raise_for_status()
        print('Sent categories to API: ' + str(response.status_code))
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
    return None


def read_file_to_array(filename):
    lines = []
    with open(filename, 'r') as file:
        for line in file:
            lines.append(line.strip())  # strip() removes newline and extra spaces
    return lines


if __name__ == '__main__':
    top_level_user_agents = read_file_to_array('resources/user_agents.csv')
    top_level_categories = read_file_to_array('resources/categories.csv')

    for category in top_level_categories:
        response = get_category_page_content(category, random.choice(top_level_user_agents))
        save_category(response.text)
        time.sleep(3)
