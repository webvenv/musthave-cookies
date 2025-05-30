#!/usr/bin/env python3

'''
Musthave-Cookies is a CLI tool that allows you to quickly identify which cookies are actually required by the server to maintain session state, access authenticated resources, or avoid redirection/denial responses.

Usage: python3 mhcookies.py request.txt 
'''

import requests
import sys
import time
from http.cookies import SimpleCookie
from urllib.parse import urlparse


class Colors:
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def colorize_status(status_code):
    if 200 <= status_code < 300:
        return f"{Colors.GREEN}{status_code}{Colors.RESET}"
    elif 300 <= status_code < 400:
        return f"{Colors.ORANGE}{status_code}{Colors.RESET}"
    elif 400 <= status_code < 500:
        return f"{Colors.RED}{status_code}{Colors.RESET}"
    elif 500 <= status_code < 600:
        return f"{Colors.BLUE}{status_code}{Colors.RESET}"
    else:
        return str(status_code)


def format_server_response(content_length, status_code, label="Server Response"):
    return f"{label.ljust(70)} [cl={str(content_length).rjust(6)}] [{colorize_status(status_code)}]"


def parse_request_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.read().splitlines()

    request_line = lines[0]
    headers = {}
    body = ''
    parsing_headers = True

    for line in lines[1:]:
        if line == '':
            parsing_headers = False
            continue
        if parsing_headers:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        else:
            body += line

    method, path, _ = request_line.split()
    host = headers.get('Host')
    url = f"https://{host}{path}" if not host.startswith(
        "http") else f"{host}{path}"

    raw_cookie_header = headers.get('Cookie', '')
    cookie = SimpleCookie()
    cookie.load(raw_cookie_header)
    cookies = {key: morsel.value for key, morsel in cookie.items()}

    return method, url, headers, body, cookies


def display_cookie_names(cookies):
    print("\n Cookies Found in Request")
    print("===================================\n")
    index_width = len(str(len(cookies)))
    for index, cookie_name in enumerate(cookies.keys(), 1):
        print(f"{str(index).rjust(index_width)}. {cookie_name}")


def send_request(method, url, headers, body, cookies_subset):
    response = requests.request(
        method,
        url,
        headers={k: v for k, v in headers.items() if k.lower() != 'cookie'},
        cookies=cookies_subset,
        data=body
    )
    return response.status_code, len(response.content)


def send_baseline_request(method, url, headers, body, all_cookies):
    print("\n\n Sending Baseline Request...")
    print("===================================")
    status, length = send_request(method, url, headers, body, all_cookies)
    print(format_server_response(length, status, "[Baseline] Server Response"))
    print("\n")
    time.sleep(2)
    return status, length


def test_each_cookie(method, url, headers, body, all_cookies, baseline_status):
    musthave = []
    for name in reversed(list(all_cookies.keys())):
        test_set = all_cookies.copy()
        del test_set[name]
        test_status, test_length = send_request(
            method, url, headers, body, test_set)
        label = f"Removing cookie: {name}"
        print(format_server_response(test_length, test_status, label))
        if test_status != baseline_status:
            musthave.append(name)
    return musthave


def print_mandatory_cookies(mandatory_cookies):
    print("\n\n Mandatory (Must-have) Cookies")
    print("===================================\n")
    if mandatory_cookies:
        for cookie in mandatory_cookies:
            print(f"+ {cookie}")
    else:
        print("  (None) — No individual cookie affected the response.\n")
        print("  This may indicate that the endpoint is publicly accessible,")
        print("  that session validation occurs elsewhere (...or the endpoint is very insecure 😅).\n")


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 mhcookies.py request.txt")
        sys.exit(1)

    request_file = sys.argv[1]

    method, url, headers, body, cookies = parse_request_file(request_file)

    display_cookie_names(cookies)

    baseline_status, baseline_length = send_baseline_request(
        method, url, headers, body, cookies)

    mandatory_cookies = test_each_cookie(
        method, url, headers, body, cookies, baseline_status)

    print_mandatory_cookies(mandatory_cookies)


if __name__ == "__main__":
    main()
