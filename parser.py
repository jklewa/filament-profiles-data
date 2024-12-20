#!/usr/bin/env python3
import argparse
import json
import re
import sys

import requests

REF_ID_PATTERN = r'[a-z0-9]+'
REF_USE_PATTERN = r'"\$(%s)"' % REF_ID_PATTERN
LINE_PATTERN = r'(%s):(.+)$' % REF_ID_PATTERN
TARGET_SEARCH_PATTERN = '{"%s":'
TARGET_ID_PATTERN = rf'"%s":\s*"\$({REF_ID_PATTERN})"'
BASE_URL = 'https://3dfilamentprofiles.com'


def fetch(resource):
    url = f'{BASE_URL}/{resource}'
    print(f'Fetching {url}...', file=sys.stderr, flush=True)
    r = requests.get(url, headers={'rsc': '1'})
    print(f'Fetched {url} status {r.status_code}', file=sys.stderr, flush=True)
    if not r.ok:
        print(f'Error: failed to fetch {url} status {r.status_code}', file=sys.stderr)
        exit(1)
    return r.content.decode('utf-8').splitlines()


def load(file_path):
    if type(file_path) is str:
        with open(file_path, 'r') as f:
            return f.read().splitlines()
    else:
        return file_path.read().splitlines()


def parse(lines, resource):
    target_ref_id = None
    fallback_ref_id = None
    line_dependencies = {}
    line_contents_by_ref_id = {"undefined": "null"}
    search_text = TARGET_SEARCH_PATTERN % resource

    for line in lines:
        match = re.match(LINE_PATTERN, line)
        if not match:
            print(f'Error: failed to parse line {line[:100]}', file=sys.stderr, flush=True)
            continue
        line_ref = match.group(1)
        ref_contents = match.group(2)

        line_dependencies[line_ref] = []
        line_contents_by_ref_id[line_ref] = ref_contents

        needed_ref_ids = re.findall(REF_USE_PATTERN, ref_contents)
        if needed_ref_ids:
            line_dependencies[line_ref].extend(needed_ref_ids)

        if search_text in ref_contents:
            target_ref_id = re.search(TARGET_ID_PATTERN % resource, ref_contents).group(1)
            fallback_ref_id = None
        if not target_ref_id and '{"data":[{' in ref_contents:
            fallback_ref_id = line_ref

    if target_ref_id is None and fallback_ref_id is None:
        print(f"Error: '{search_text}' not found", file=sys.stderr)
        exit(1)

    for refID, dependencies in line_dependencies.items():
        line_contents = line_contents_by_ref_id[refID]

        for neededRefID in dependencies:
            if neededRefID in line_contents_by_ref_id:
                line_contents = line_contents.replace('"$' + neededRefID + '"', line_contents_by_ref_id[neededRefID])
            else:
                print(f'Error: missing reference {neededRefID} for {refID}', file=sys.stderr, flush=True)

        line_contents_by_ref_id[refID] = line_contents

    if target_ref_id is not None:
        target_data = json.loads(line_contents_by_ref_id[target_ref_id])
        return target_data

    def find_data_node(node):
        if isinstance(node, dict):
            if "data" in node:
                return node["data"]
            for key, value in node.items():
                result = find_data_node(value)
                if result:
                    return result
        elif isinstance(node, list):
            for item in node:
                result = find_data_node(item)
                if result:
                    return result
        return None

    fallback_data = line_contents_by_ref_id[fallback_ref_id]
    target_data = find_data_node(json.loads(fallback_data))
    if target_data is None:
        print(f"Error in fallback search", file=sys.stderr)
        exit(1)
    return target_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    source_group = parser.add_argument_group('Source')
    resources = ['filaments', 'brands', 'materials', 'dryers']
    source_group.add_argument('--fetch', type=str, choices=resources, metavar="RESOURCE", help='Fetch one of: %(choices)s')
    source_group.add_argument('--file', type=argparse.FileType('r'), help='path to the file to parse')
    parser_group = parser.add_argument_group('Parse')
    parser_group.add_argument('--resource', type=str, choices=resources, metavar="RESOURCE", help='Parse one of: %(choices)s; defaults to --fetch')
    args = parser.parse_args()
    if args.fetch:
        args.resource = args.fetch
        data_lines = fetch(args.fetch)
        data = parse(data_lines, args.resource)
    elif args.file and not args.resource:
        parser.error('--resource is required when using --file')
    elif args.file:
        data_lines = load(args.file)
        data = parse(data_lines, args.resource)
    else:
        parser.error('Either --fetch or --file is required')
    print(json.dumps(data, indent=2))
