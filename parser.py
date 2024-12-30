#!/usr/bin/env python3
import argparse
import getpass
import json
import os
import re
import sys
from collections import defaultdict
from typing import List, Tuple

import requests
from dotenv import load_dotenv, set_key

# Load environment variables
ENV_FILE = ".env"
load_dotenv(ENV_FILE)

BASE_URL = "https://3dfilamentprofiles.com"
RESOURCE_KEY_MAP = {"myfilaments": "filaments"}
REF_ID_PATTERN = r"[a-z0-9]+"
REF_USE_PATTERN = r'"\$(%s)"' % REF_ID_PATTERN
LINE_PATTERN = r"(%s):(.+)$" % REF_ID_PATTERN
TARGET_SEARCH_PATTERN = '{"%s":'
TARGET_ID_PATTERN = rf'"%s":\s*"\$({REF_ID_PATTERN})"'
LOGIN_NEXT_ACTION_PATTERN = r'type="submit" name="\$ACTION_ID_([a-z0-9]+)"'


def new_session():
    """Get a new requests.Session."""
    s = requests.sessions.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    return s


def get_auth_session():
    """Get an authenticated requests.Session."""
    session = new_session()
    cookies = os.getenv("AUTH_COOKIES", "").strip()
    if len(cookies) == 0:
        print(
            f"Error: Missing AUTH_COOKIES, try {sys.argv[0]} --login", file=sys.stderr
        )
        exit(1)
    for cookie in cookies.split(";"):
        try:
            name, value = cookie.strip().split("=", 2)
            session.cookies.set(name, value)
        except ValueError:
            print(f"Error: Invalid format for AUTH_COOKIES: {cookie}", file=sys.stderr)
            exit(1)
    return session


def save_auth(cookies: List[Tuple[str, str]]):
    """Save authentication cookies to .env file."""
    set_key(ENV_FILE, "AUTH_COOKIES", "; ".join("=".join(cookie) for cookie in cookies))
    print("Auth saved to .env", file=sys.stderr)


def login():
    """Login to 3dfilamentprofiles.com and save the token."""
    email = input("Email: ")
    password = getpass.getpass("Password: ")

    login_next_action = re.search(
        LOGIN_NEXT_ACTION_PATTERN, requests.get(f"{BASE_URL}/login").text
    ).group(1)
    print("Logging in...", file=sys.stderr)
    headers = {
        "accept": "text/x-component",
        "dnt": "1",
        "next-action": login_next_action,
    }
    form_data = {
        "1_email": email,
        "1_password": password,
        "0": '["$K1"]',
    }
    r = requests.post(
        f"{BASE_URL}/login", data=form_data, headers=headers, allow_redirects=True
    )

    if "Invalid+login+credentials" in r.headers.get("X-Action-Redirect", ""):
        print("Error: Invalid login credentials", file=sys.stderr)
        exit(1)

    # Extract auth cookies
    auth_cookies = [(c.name, c.value) for c in r.cookies if "auth-token" in c.name]

    # r.status_code is `303 See Other` on successful login
    if r.status_code >= 400 or not auth_cookies:
        print(f"Login failed: {r.status_code}", file=sys.stderr)
        print("Response headers:", file=sys.stderr)
        for k, v in r.headers.items():
            print(f"{k}: {v}", file=sys.stderr)
        print("Response cookies:", file=sys.stderr)
        for cookie in r.cookies:
            print(f"{cookie.name}: {cookie.value}", file=sys.stderr)
        print("\nResponse content:", file=sys.stderr)
        print(r.text, file=sys.stderr)
        exit(1)

    save_auth(auth_cookies)
    print("Login successful!", file=sys.stderr)


def fetch(resource):
    """Fetch data from the API with authentication support for myfilaments."""
    if resource == "myfilaments":
        url = f"{BASE_URL}/my/filaments"
        session = get_auth_session()
    else:
        url = f"{BASE_URL}/{resource}"
        session = new_session()
    print(f"Fetching {url}...", file=sys.stderr, flush=True)
    r = session.get(url, headers={"rsc": "1"})
    if "NEXT_REDIRECT;replace;/login" in r.content.decode("utf-8"):
        print("Error: Bad auth", file=sys.stderr)
        exit(1)
    print(f"Fetched {url} status {r.status_code}", file=sys.stderr, flush=True)
    if not r.ok:
        print(f"Error: failed to fetch {url} status {r.status_code}", file=sys.stderr)
        exit(1)
    return r.content.decode("utf-8").splitlines()


def load(file_path):
    if type(file_path) is str:
        with open(file_path, "r") as f:
            return f.read().splitlines()
    else:
        return file_path.read().splitlines()


def parse(lines, resource):
    target_ref_id = None
    fallback_ref_ids = []
    line_dependencies = {}
    line_contents_by_ref_id = {"undefined": "null"}
    resource_key = RESOURCE_KEY_MAP.get(resource, resource)
    search_text = TARGET_SEARCH_PATTERN % resource_key

    for line in lines:
        match = re.match(LINE_PATTERN, line)
        if not match:
            print(
                f"Error: failed to parse line {line[:100]}", file=sys.stderr, flush=True
            )
            continue
        line_ref = match.group(1)
        ref_contents = match.group(2)

        line_dependencies[line_ref] = []
        line_contents_by_ref_id[line_ref] = ref_contents

        needed_ref_ids = re.findall(REF_USE_PATTERN, ref_contents)
        if needed_ref_ids:
            line_dependencies[line_ref].extend(needed_ref_ids)

        if search_text in ref_contents:
            target_ref_id = re.search(
                TARGET_ID_PATTERN % resource_key, ref_contents
            ).group(1)
        if '{"data":[{' in ref_contents:  # This assumes at least one data entry
            fallback_ref_ids.append(line_ref)

    if target_ref_id is None and not fallback_ref_ids:
        print(f"Error: '{search_text}' not found", file=sys.stderr)
        exit(1)

    for refID, dependencies in line_dependencies.items():
        line_contents = line_contents_by_ref_id[refID]

        for neededRefID in dependencies:
            if neededRefID in line_contents_by_ref_id:
                line_contents = line_contents.replace(
                    '"$' + neededRefID + '"', line_contents_by_ref_id[neededRefID]
                )
            else:
                print(
                    f"Error: missing reference {neededRefID} for {refID}",
                    file=sys.stderr,
                    flush=True,
                )

        line_contents_by_ref_id[refID] = line_contents

    parsed_data = {}

    if target_ref_id is not None:
        target_data = json.loads(line_contents_by_ref_id[target_ref_id])
        parsed_data[resource_key] = target_data

    def find_data_nodes(node, flatten=True) -> dict:
        nodes = defaultdict(list)
        if isinstance(node, dict):
            if "data" in node:
                data_type = node.get("dataType", resource_key)
                data_type += "s" if data_type[-1] != "s" else ""
                nodes[data_type].append(node["data"])
            for key, value in node.items():
                result = find_data_nodes(value, flatten=False)
                for r, v in result.items():
                    nodes[r].extend(v)
        elif isinstance(node, list):
            for item in node:
                result = find_data_nodes(item, flatten=False)
                for r, v in result.items():
                    nodes[r].extend(v)
        if flatten:
            flattened_nodes = {}
            for k, v in nodes.items():
                if len(v) == 1:
                    flattened_nodes[k] = v[0]
                else:
                    # Order by length, descending
                    v.sort(key=lambda x: len(str(x)), reverse=True)
                    for i, item in enumerate(v):
                        new_key = f"{k}.{i+1}" if i > 0 else k
                        flattened_nodes[new_key] = item
            return flattened_nodes

        return nodes

    for fallback_ref_id in fallback_ref_ids:
        fallback_contents = line_contents_by_ref_id[fallback_ref_id]
        data_nodes = find_data_nodes(json.loads(fallback_contents))
        parsed_data.update(data_nodes)

    if resource == "myfilaments":
        for k, v in parsed_data.items():
            if not isinstance(v, list):
                continue
            for item in v:
                try:
                    item["price_data"] = json.loads(item["price_data"])
                except (TypeError, json.JSONDecodeError):
                    continue

    return parsed_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # Add login command
    login_group = parser.add_argument_group("Login")
    login_group.add_argument(
        "--login",
        action="store_true",
        help="Login to 3dfilamentprofiles.com (only used by 'myfilaments')",
    )

    # Add fetch/parse commands
    source_group = parser.add_argument_group("Source")
    resources = ["filaments", "brands", "materials", "dryers", "myfilaments"]
    source_group.add_argument(
        "--fetch",
        type=str,
        choices=resources,
        metavar="RESOURCE",
        help="Fetch one of: %(choices)s",
    )
    source_group.add_argument(
        "--file", type=argparse.FileType("r"), help="path to the file to parse"
    )
    parser_group = parser.add_argument_group("Parse")
    parser_group.add_argument(
        "--resource",
        type=str,
        choices=resources,
        metavar="RESOURCE",
        help="Parse one of: %(choices)s; defaults to --fetch",
    )
    args = parser.parse_args()

    if args.login:
        login()
        exit(0)
    elif args.fetch:
        args.resource = args.fetch
        data_lines = fetch(args.fetch)
        data = parse(data_lines, args.resource)
    elif args.file and not args.resource:
        parser.error("--resource is required when using --file")
    elif args.file:
        data_lines = load(args.file)
        data = parse(data_lines, args.resource)
    else:
        parser.error("Either --fetch or --file is required")
    print(json.dumps(data, indent=2))
