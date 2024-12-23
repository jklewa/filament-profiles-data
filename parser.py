#!/usr/bin/env python3
import argparse
import json
import re
import sys

import requests

REF_ID_PATTERN = r"[a-z0-9]+"
REF_USE_PATTERN = r'"\$(%s)"' % REF_ID_PATTERN
LINE_PATTERN = r"(%s):(.+)$" % REF_ID_PATTERN
TARGET_SEARCH_PATTERN = '{"%s":'
TARGET_ID_PATTERN = rf'"%s":\s*"\$({REF_ID_PATTERN})"'
BASE_URL = "https://3dfilamentprofiles.com"
RESOURCE_KEY_MAP = {"myfilaments": "filaments"}


def fetch(resource):
    url = f"{BASE_URL}/{resource}"
    print(f"Fetching {url}...", file=sys.stderr, flush=True)
    r = requests.get(url, headers={"rsc": "1"})
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
        if '{"data":[{' in ref_contents:
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

    def find_data_nodes(node) -> dict:
        nodes = {}
        if isinstance(node, dict):
            if "data" in node:
                data_type = node.get("dataType", resource_key)
                data_type += "s" if data_type[-1] != "s" else ""
                nodes[data_type] = node["data"]
            for key, value in node.items():
                result = find_data_nodes(value)
                if result:
                    nodes.update(result)
        elif isinstance(node, list):
            for item in node:
                result = find_data_nodes(item)
                if result:
                    nodes.update(result)
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
    source_group = parser.add_argument_group("Source")
    resources = ["filaments", "brands", "materials", "dryers"]
    parsable = resources + ["myfilaments"]
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
        choices=parsable,
        metavar="RESOURCE",
        help="Parse one of: %(choices)s; defaults to --fetch",
    )
    args = parser.parse_args()
    if args.fetch:
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
