#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

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

# Retry settings
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 5
_BACKOFF_BASE = 2.0   # seconds; doubles each retry


def new_session():
    """Get a new requests.Session."""
    s = requests.sessions.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    return s


def get_auth_session():
    """Get an authenticated requests.Session."""
    session = new_session()
    cookies = os.getenv("AUTH_COOKIES", "").strip()
    if not cookies:
        print("Error: Missing AUTH_COOKIES, see .env.example", file=sys.stderr)
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


def _get(session, url, debug=False):
    """
    GET url with rsc:1 header. Retries on 429/5xx with exponential backoff.
    Returns response lines on success, None on permanent failure.
    """
    if debug:
        print(f"DEBUG: GET {url}", file=sys.stderr)
    delay = _BACKOFF_BASE
    for attempt in range(_MAX_RETRIES):
        try:
            r = session.get(url, headers={"rsc": "1"}, timeout=30)
        except requests.RequestException as e:
            print(f"  Request error ({url}): {e}, retrying in {delay:.0f}s...", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
            continue

        if "NEXT_REDIRECT;replace;/login" in r.content.decode("utf-8", errors="replace"):
            print("Error: Bad auth", file=sys.stderr)
            exit(1)

        if r.status_code in _RETRY_STATUSES:
            retry_after = int(r.headers.get("Retry-After", delay))
            wait = max(retry_after, delay)
            print(f"  HTTP {r.status_code} ({url}), retrying in {wait:.0f}s...", file=sys.stderr)
            time.sleep(wait)
            delay *= 2
            continue

        if not r.ok:
            print(f"  HTTP {r.status_code} ({url}), giving up.", file=sys.stderr)
            return None

        return r.content.decode("utf-8").splitlines()

    print(f"  Max retries exceeded for {url}", file=sys.stderr)
    return None

# ---------------------------------------------------------------------------
# RSC parsing helpers
# ---------------------------------------------------------------------------

def _extract_rsc_objects(lines, debug=False):
    """
    Walk RSC lines, resolve $ref references, return list of (ref, parsed_obj)
    for every line whose content parses as JSON.
    """
    line_contents = {"undefined": "null"}
    line_deps = {}

    for line in lines:
        m = re.match(LINE_PATTERN, line)
        if not m:
            if debug:
                print(f"DEBUG: skipping non-matching line: {line[:80]}", file=sys.stderr)
            continue
        ref = m.group(1)
        content = m.group(2)
        line_deps[ref] = re.findall(REF_USE_PATTERN, content)
        line_contents[ref] = content

    for ref in line_deps:
        content = line_contents[ref]
        for needed in line_deps[ref]:
            if needed in line_contents:
                content = content.replace('"$' + needed + '"', line_contents[needed])
        line_contents[ref] = content

    results = []
    for ref, content in line_contents.items():
        if ref == "undefined":
            continue
        if not content.startswith("{") and not content.startswith("["):
            continue
        try:
            obj = json.loads(content)
            results.append((ref, obj))
        except json.JSONDecodeError:
            pass
    return results


def _find_in_obj(obj, predicate, results=None):
    """Recursively find all objects matching predicate."""
    if results is None:
        results = []
    if predicate(obj):
        results.append(obj)
    if isinstance(obj, dict):
        for v in obj.values():
            _find_in_obj(v, predicate, results)
    elif isinstance(obj, list):
        for item in obj:
            _find_in_obj(item, predicate, results)
    return results


# ---------------------------------------------------------------------------
# Paginated flat list: discover all (brand, material, type) combos
# ---------------------------------------------------------------------------

def _fetch_filaments_page(session, page, page_size=100, debug=False):
    """
    Fetch one page of /filaments?page=N&pageSize=N.
    Returns (list_of_minimal_dicts, page_count).
    """
    url = f"{BASE_URL}/filaments?page={page}&pageSize={page_size}"
    lines = _get(session, url, debug=debug)
    if lines is None:
        return [], 0

    parsed = _extract_rsc_objects(lines)
    filaments = []
    page_count = 0

    def is_filament_card(o):
        return (
            isinstance(o, dict)
            and "id" in o
            and "brand_key" in o
            and "material_key" in o
            and "material_type_key" in o
            and "color" in o
            and "created_by" in o
        )

    for ref, obj in parsed:
        if not page_count:
            found_pc = _find_in_obj(obj, lambda o: isinstance(o, dict) and "pageCount" in o)
            if found_pc:
                page_count = found_pc[0]["pageCount"]
                if debug:
                    print(f"DEBUG: pageCount={page_count}", file=sys.stderr)
        for f in _find_in_obj(obj, is_filament_card):
            filaments.append({
                "id": f["id"],
                "brand_key": f["brand_key"],
                "brand_name": f.get("brand_name", ""),
                "material_key": f["material_key"],
                "material": f.get("material", ""),
                "material_type_key": f["material_type_key"],
                "material_type": f.get("material_type", ""),
                "color": f.get("color", ""),
                "discontinued": f.get("discontinued"),
                "created_by": f.get("created_by"),
                "users_with_spools": f.get("users_with_spools"),
            })

    seen = set()
    unique = [f for f in filaments if not (f["id"] in seen or seen.add(f["id"]))]

    if debug:
        print(f"DEBUG: page={page} got {len(unique)} filaments, page_count={page_count}", file=sys.stderr)
    return unique, page_count


def _all_combos_from_list(session, page_size=100, debug=False):
    """
    Page through the flat list and return (all_minimal_filaments, ordered_combos_dict).
    combos keys are (brand_key, material_key, material_type_key).
    """
    print("Paging through filament list to find all brand/material/type combos...",
          file=sys.stderr, flush=True)
    all_minimal = []
    first, page_count = _fetch_filaments_page(session, 1, page_size, debug=debug)
    all_minimal.extend(first)

    if not page_count:
        print("Warning: could not determine page count", file=sys.stderr)
    else:
        for page in range(2, page_count + 1):
            print(f"  Page {page}/{page_count} ({len(all_minimal)} filaments so far)...",
                  file=sys.stderr, flush=True)
            batch, _ = _fetch_filaments_page(session, page, page_size, debug=debug)
            all_minimal.extend(batch)
            time.sleep(0.15)

    combos = {}
    for f in all_minimal:
        key = (f["brand_key"], f["material_key"], f["material_type_key"])
        combos.setdefault(key, f)

    print(f"  {len(all_minimal)} filaments, {len(combos)} unique combos.", file=sys.stderr)
    return all_minimal, combos


# ---------------------------------------------------------------------------
# Filter pages: /filaments/{brand}/{material}/{type} -> rich rows
# ---------------------------------------------------------------------------

def _fetch_filter_rows(session, brand_key, material_key, material_type_key, debug=False):
    """
    Fetch /filaments/{brand}/{material}/{type} and return rich row dicts
    (includes rgb, ASIN, updated_at, website, price, td_value).
    """
    url = f"{BASE_URL}/filaments/{brand_key}/{material_key}/{material_type_key}"
    lines = _get(session, url, debug=debug)
    if lines is None:
        return []

    parsed = _extract_rsc_objects(lines)

    def is_rich_row(o):
        return (
            isinstance(o, dict)
            and "id" in o
            and "brand_key" in o
            and "updated_at" in o
            and "material_key" in o
        )

    rows = []
    seen_ids = set()
    for ref, obj in parsed:
        # Prefer the explicit {"rows": [...]} container
        if isinstance(obj, dict) and "rows" in obj and isinstance(obj["rows"], list):
            for row in obj["rows"]:
                if is_rich_row(row) and row["id"] not in seen_ids:
                    seen_ids.add(row["id"])
                    rows.append(row)
        for row in _find_in_obj(obj, is_rich_row):
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                rows.append(row)

    if debug:
        print(f"DEBUG: {brand_key}/{material_key}/{material_type_key} -> {len(rows)} rows",
              file=sys.stderr)
    return rows


# ---------------------------------------------------------------------------
# Defaults: /defaults/{brand}/{material}/{type} -> properties
# ---------------------------------------------------------------------------

def _fetch_defaults_item(session, brand_key, material_key, material_type_key, debug=False):
    """
    Fetch /defaults/{brand}/{material}/{type} and return the item dict
    with properties (temp_min/max, bed_temp, fan_speed, flow_ratio, etc.)
    and created_at / updated_at.
    """
    url = f"{BASE_URL}/defaults/{brand_key}/{material_key}/{material_type_key}"
    lines = _get(session, url, debug=debug)
    if lines is None:
        return None

    parsed = _extract_rsc_objects(lines)

    def is_defaults_item(o):
        return (
            isinstance(o, dict)
            and "brand_key" in o
            and "material_key" in o
            and "properties" in o
            and isinstance(o.get("properties"), dict)
        )

    for ref, obj in parsed:
        if isinstance(obj, dict) and is_defaults_item(obj.get("item", {})):
            if debug:
                print(f"DEBUG: defaults item found via 'item' key, ref={ref}", file=sys.stderr)
            return obj["item"]
        found = _find_in_obj(obj, is_defaults_item)
        if found:
            if debug:
                print(f"DEBUG: defaults item found recursively, ref={ref}", file=sys.stderr)
            return found[0]

    if debug:
        print(f"DEBUG: no defaults item for {brand_key}/{material_key}/{material_type_key}",
              file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Top-level fetch: filaments (full enriched) + other resources
# ---------------------------------------------------------------------------

_PROPS_FIELDS = (
    "temp_max", "temp_min", "bed_temp_max", "bed_temp_min",
    "fan_speed_max", "fan_speed_min", "flow_ratio",
    "softening_temp", "max_volumetric_speed", "spool_weight", "adapter_url",
)

# Number of concurrent combo fetches. Each combo makes 2 requests (filter + defaults).
# 10 workers keeps total in-flight requests reasonable without hammering the server.
_FETCH_WORKERS = 10


def _fetch_combo(combo_key, debug=False):
    """
    Fetch rich rows + defaults for one (brand, material, type) combo.
    Returns (combo_key, rows, defaults_item). Uses its own session per thread.
    """
    brand_key, material_key, material_type_key = combo_key
    session = new_session()
    rows = _fetch_filter_rows(session, brand_key, material_key, material_type_key,
                               debug=debug)
    item = _fetch_defaults_item(session, brand_key, material_key, material_type_key,
                                 debug=debug)
    return combo_key, rows, item


def fetch_filaments(debug=False):
    """
    Fetch all filaments with full data:
    1. Page through /filaments to collect all (brand, material, type) combos.
    2. Concurrently fetch /filaments/{brand}/{material}/{type} for rich rows
       (rgb, ASIN, updated_at, website, price, td_value) and
       /defaults/{brand}/{material}/{type} for slicer properties.
    3. Merge defaults properties into each filament row.

    Returns {"filaments": [...]} ready for bambu_lab.py.
    """
    session = new_session()
    _, combos = _all_combos_from_list(session, page_size=100, debug=debug)
    sorted_combos = sorted(combos.keys())
    total = len(sorted_combos)

    print(f"Fetching rich rows + defaults for {total} combos "
          f"({_FETCH_WORKERS} concurrent)...", file=sys.stderr, flush=True)

    defaults_map = {}
    all_rich = []
    seen_ids = set()
    done = 0

    with ThreadPoolExecutor(max_workers=_FETCH_WORKERS) as pool:
        futures = {pool.submit(_fetch_combo, key, debug): key
                   for key in sorted_combos}
        for future in as_completed(futures):
            done += 1
            combo_key, rows, item = future.result()
            brand_key, material_key, material_type_key = combo_key
            if done % 50 == 0 or done == total:
                print(f"  [{done}/{total}] last: {brand_key}/{material_key}/{material_type_key}",
                      file=sys.stderr, flush=True)
            for row in rows:
                if row["id"] not in seen_ids:
                    seen_ids.add(row["id"])
                    all_rich.append(row)
            if item:
                defaults_map[combo_key] = item

    print(f"Merging defaults into {len(all_rich)} filaments...", file=sys.stderr)
    for row in all_rich:
        key = (row.get("brand_key"), row.get("material_key"), row.get("material_type_key"))
        item = defaults_map.get(key)
        if not item:
            continue
        dp = item.get("properties") or {}
        for ts in ("created_at", "updated_at"):
            if not row.get(ts) and item.get(ts):
                row[ts] = item[ts]
        if not row.get("properties"):
            row["properties"] = {f: dp.get(f) for f in _PROPS_FIELDS}
        if not row.get("default_properties"):
            row["default_properties"] = {f: dp.get(f) for f in _PROPS_FIELDS}

    print(f"Done. {len(all_rich)} filaments collected.", file=sys.stderr)
    return {"filaments": all_rich}


def fetch_simple(resource, debug=False):
    """Single-URL fetch for brands, materials, dryers, myfilaments."""
    if resource == "myfilaments":
        url = f"{BASE_URL}/my/filaments"
        session = get_auth_session()
    else:
        url = f"{BASE_URL}/{resource}"
        session = new_session()
    print(f"Fetching {url}...", file=sys.stderr, flush=True)
    lines = _get(session, url, debug=debug)
    if lines is None:
        exit(1)
    return lines


# ---------------------------------------------------------------------------
# Legacy RSC line-based parser (--file and myfilaments)
# ---------------------------------------------------------------------------

def load(file_path):
    if isinstance(file_path, str):
        with open(file_path, "r") as f:
            return f.read().splitlines()
    return file_path.read().splitlines()


def parse(lines, resource, debug=False):
    target_ref_id = None
    fallback_ref_ids = []
    line_dependencies = {}
    line_contents_by_ref_id = {"undefined": "null"}
    resource_key = RESOURCE_KEY_MAP.get(resource, resource)
    search_text = TARGET_SEARCH_PATTERN % resource_key

    if debug:
        print(f"DEBUG: resource={resource}, resource_key={resource_key}, "
              f"search_text={search_text!r}", file=sys.stderr)

    for line in lines:
        match = re.match(LINE_PATTERN, line)
        if not match:
            print(f"Error: failed to parse line {line[:100]}", file=sys.stderr, flush=True)
            continue
        line_ref = match.group(1)
        ref_contents = match.group(2)
        line_dependencies[line_ref] = []
        line_contents_by_ref_id[line_ref] = ref_contents

        needed_ref_ids = re.findall(REF_USE_PATTERN, ref_contents)
        if needed_ref_ids:
            line_dependencies[line_ref].extend(needed_ref_ids)

        if search_text in ref_contents:
            if debug:
                print(f"DEBUG: found search_text in line ref={line_ref}", file=sys.stderr)
            target_match = re.search(TARGET_ID_PATTERN % resource_key, ref_contents)
            if target_match:
                target_ref_id = target_match.group(1)
                if debug:
                    print(f"DEBUG: target_ref_id={target_ref_id!r}", file=sys.stderr)
            elif debug:
                print(f"DEBUG: TARGET_ID_PATTERN no match, snippet={ref_contents[:300]}",
                      file=sys.stderr)

        if '{"data":[{' in ref_contents:
            fallback_ref_ids.append(line_ref)
        singular_key = resource_key[:-1] if resource_key.endswith("s") else resource_key
        if f'"{singular_key}":{{"id":' in ref_contents:
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
                print(f"Error: missing reference {neededRefID} for {refID}",
                      file=sys.stderr, flush=True)
        line_contents_by_ref_id[refID] = line_contents

    parsed_data = {}
    if target_ref_id is not None:
        parsed_data[resource_key] = json.loads(line_contents_by_ref_id[target_ref_id])

    def find_data_nodes(node, flatten=True):
        nodes = defaultdict(list)
        if isinstance(node, dict):
            if "data" in node:
                data_type = node.get("dataType", resource_key)
                data_type += "s" if data_type[-1] != "s" else ""
                nodes[data_type].append(node["data"])
            singular_key = resource_key[:-1] if resource_key.endswith("s") else resource_key
            if singular_key in node and isinstance(node[singular_key], dict) and "id" in node[singular_key]:
                nodes[resource_key].append(node[singular_key])
            for value in node.values():
                for r, v in find_data_nodes(value, flatten=False).items():
                    nodes[r].extend(v)
        elif isinstance(node, list):
            for item in node:
                for r, v in find_data_nodes(item, flatten=False).items():
                    nodes[r].extend(v)
        if flatten:
            flattened = {}
            for k, v in nodes.items():
                v.sort(key=lambda x: len(str(x)), reverse=True)
                for i, item in enumerate(v):
                    flattened[f"{k}.{i+1}" if i > 0 else k] = item
            return flattened
        return nodes

    merged_inline = defaultdict(list)
    for fallback_ref_id in fallback_ref_ids:
        try:
            parsed_node = json.loads(line_contents_by_ref_id[fallback_ref_id])
        except json.JSONDecodeError as e:
            if debug:
                print(f"DEBUG: JSON parse failed ref={fallback_ref_id}: {e}", file=sys.stderr)
            continue
        for k, v in find_data_nodes(parsed_node, flatten=False).items():
            merged_inline[k].extend(v)

    for k, v in merged_inline.items():
        parsed_data[k] = v

    if debug:
        summary = {k: len(v) if isinstance(v, list) else type(v).__name__
                   for k, v in parsed_data.items()}
        print(f"DEBUG: parsed_data keys/lengths: {summary}", file=sys.stderr)

    if resource == "myfilaments":
        for v in parsed_data.values():
            if not isinstance(v, list):
                continue
            for item in v:
                try:
                    item["price_data"] = json.loads(item["price_data"])
                except (TypeError, json.JSONDecodeError):
                    pass

    return parsed_data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch and parse filament data from 3dfilamentprofiles.com"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    source_group = parser.add_argument_group("Source")
    all_resources = ["filaments", "brands", "materials", "dryers", "myfilaments"]
    source_group.add_argument(
        "--fetch",
        type=str,
        choices=all_resources,
        metavar="RESOURCE",
        help=(
            "Fetch one of: %(choices)s. "
            "'filaments' fetches all filaments with full slicer properties merged in."
        ),
    )
    source_group.add_argument(
        "--file", type=argparse.FileType("r"), help="Path to a raw RSC file to parse"
    )

    parser_group = parser.add_argument_group("Parse")
    parser_group.add_argument(
        "--resource",
        type=str,
        choices=all_resources + ["raw"],
        metavar="RESOURCE",
        help="Resource type for --file parsing. One of: %(choices)s",
    )

    args = parser.parse_args()
    debug = args.debug

    if args.fetch == "filaments":
        data = fetch_filaments(debug=debug)
        print(json.dumps(data, indent=2))

    elif args.fetch in ("brands", "materials", "dryers", "myfilaments"):
        resource = args.fetch
        args.resource = args.resource or resource
        data_lines = fetch_simple(resource, debug=debug)
        if args.resource == "raw":
            print("\n".join(data_lines))
            exit(0)
        data = parse(data_lines, args.resource, debug=debug)
        print(json.dumps(data, indent=2))

    elif args.file and not args.resource:
        parser.error("--resource is required when using --file")

    elif args.file:
        data_lines = load(args.file)
        data = parse(data_lines, args.resource, debug=debug)
        print(json.dumps(data, indent=2))

    else:
        parser.error("Either --fetch or --file is required")
