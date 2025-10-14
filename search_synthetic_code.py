#!/usr/bin/env python3
"""
Find Synthetics monitors whose script contains any of a set of strings.

What it does:
  1) Uses NerdGraph to enumerate all Synthetic monitors and their GUIDs.
  2) Uses the Synthetics REST API to fetch each monitor's script text.
  3) Searches for each target string (case-insensitive) within the script.
  4) Writes results to CSV and prints a concise summary.

Prereqs:
  pip install requests tqdm

Env vars (or edit the CONFIG block below):
  NEW_RELIC_API_KEY   -> User/Personal API key (NRAK-...)
  NEW_RELIC_ACCOUNT_ID-> Your New Relic account ID (integer)
  NEW_RELIC_REGION    -> "US" (default) or "EU"
"""

import csv
import os
import sys
import time
import requests
import base64
from tqdm import tqdm
from dotenv import load_dotenv

# ---------------------- CONFIG ----------------------
TARGET_STRINGS = [
    # <-- Put the strings you want to search for here -->
    "insightglobal.com",
    "insightglobal.net",
    "monumentconsulting.com",
    "igatlis.com",
    "igevergreen.com",
    "insightglobal-msd.com",
    "insightglobal.co.uk",
    "insightglobalservices.co.uk",
    "igcompass.com",
    "igfamilyfoundation.org",
    "igimail.com",
    "cotiviti-igmsd.com",
    "msd.insightglobal.com",
]

load_dotenv()
API_KEY      = os.getenv('NR_API_KEY')
ACCOUNT_ID   = os.getenv('ACCOUNT_ID')
REGION       = os.getenv("NEW_RELIC_REGION", "US").strip().upper()  # "US" or "EU"

OUTPUT_CSV   = "synthetics_string_hits.csv"
CASE_SENSITIVE = False  # set True if you want case-sensitive matches

# Throttle between script fetches to be polite (in seconds)
SCRIPT_FETCH_DELAY = 0.05
# ---------------------------------------------------

if not API_KEY or not ACCOUNT_ID:
    print("ERROR: Please set NEW_RELIC_API_KEY and NEW_RELIC_ACCOUNT_ID env vars (or edit the script).")
    sys.exit(1)

if REGION not in ("US", "EU"):
    print('ERROR: NEW_RELIC_REGION must be "US" or "EU".')
    sys.exit(1)

GRAPHQL_URL = "https://api.newrelic.com/graphql" if REGION == "US" else "https://api.eu.newrelic.com/graphql"
SYNTHETICS_BASE = (
    "https://synthetics.newrelic.com/synthetics/api/v3"
    if REGION == "US"
    else "https://synthetics.eu.newrelic.com/synthetics/api/v3"
)

headers_graphql = {
    "Content-Type": "application/json",
    "API-Key": API_KEY,  # NerdGraph header
}
headers_synthetics = {
    "Accept": "application/json",
    "Api-Key": API_KEY,  # Synthetics v3 REST header (note the casing)
}

def nrql_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def fetch_all_synthetics():
    """
    Use NerdGraph entitySearch to get all Synthetic monitors (guids & basic metadata).
    Returns a list of dicts with keys: guid, name, monitorType (if available)
    """
    query = """
    {
      actor {
        user {
          name
        }
        entitySearch(queryBuilder: {type: MONITOR}) {
          results {
            entities {
              name
              ... on SyntheticMonitorEntityOutline {
                monitorType
                monitorId
              }
            }
            nextCursor
          }
        }
      }
    }
    """

    monitors = []
    cursor = None
    while True:
        payload = {"query": query, "variables": {"cursor": cursor}}
        resp = requests.post(GRAPHQL_URL, json=payload, headers=headers_graphql, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        try:
            res = data["data"]["actor"]["entitySearch"]["results"]
        except Exception:
            print("Unexpected NerdGraph response:", data)
            raise

        print(res)

        ents = res.get("entities", []) or []
        for e in ents:
            if e.get("monitorType") == "SCRIPT_BROWSER":
                monitors.append({
                    "guid": e.get("monitorId"),
                    "name": e.get("name"),
                    "monitorType": e.get("monitorType"),
                })

        cursor = res.get("nextCursor")
        if not cursor:
            break

    return monitors

def fetch_script_for_monitor(guid: str) -> str:
    """
    GET /monitors/{guid}/script from Synthetics v3
    Returns script text or "" if not present (e.g., for non-scripted monitors).
    """
    url = f"{SYNTHETICS_BASE}/monitors/{guid}/script"
    r = requests.get(url, headers=headers_synthetics, timeout=60)
    if r.status_code == 404:
        # Not a scripted monitor or no script available
        return ""
    r.raise_for_status()
    j = r.json()
    # Different accounts can see 'scriptText' or 'script' depending on API version/shape
    return j.get("scriptText") or j.get("script") or ""


def main():
    print(f"Region: {REGION}")
    print("Fetching Synthetics monitor inventory via NerdGraph...")
    monitors = fetch_all_synthetics()
    if not monitors:
        print("No Synthetics monitors found.")
        return

    # Prefetch scripts for all monitors once (to avoid re-fetch per string)
    scripts = {}
    print(f"Fetching scripts for {len(monitors)} monitors...")
    for m in tqdm(monitors, unit="mon", smoothing=0.1):
    # for m in monitors:
        guid = m["guid"]
        try:
            # script = fetch_script_for_monitor(guid)
            script = base64.b64decode(fetch_script_for_monitor(guid)).decode('utf-8')
        except requests.HTTPError as e:
            # Continue on errors; log minimal info
            script = ""
            sys.stderr.write(f"[WARN] Failed to fetch script for {m.get('name')} ({guid}): {e}\n")
        scripts[guid] = script
        if SCRIPT_FETCH_DELAY:
            time.sleep(SCRIPT_FETCH_DELAY)

    # Prepare search
    targets = TARGET_STRINGS[:]
    if not CASE_SENSITIVE:
        targets_norm = [t.lower() for t in targets]
    else:
        targets_norm = targets

    # Build index of matches: { target_string : [ monitor dicts... ] }
    results = {t: [] for t in targets}

    print("Scanning scripts for target strings...")
    for m in monitors:
        guid = m["guid"]
        script = scripts.get(guid, "") or ""
        if not script:
            continue

        hay = script if CASE_SENSITIVE else script.lower()
        for original, needle in zip(targets, targets_norm):
            if needle in hay:
                results[original].append(m)

    # Write CSV and show summary
    total_hits = 0
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["search_string", "monitor_name", "monitor_guid", "monitor_type"])
        for s in targets:
            hits = results[s]
            if hits:
                for m in hits:
                    w.writerow([s, m.get("name"), m.get("guid"), m.get("monitorType")])
                total_hits += len(hits)

    print("\n=== Summary ===")
    for s in targets:
        hits = results[s]
        if hits:
            print(f"'{s}': {len(hits)} monitor(s)")
            # show top few names
            for m in hits[:5]:
                print(f"  - {m.get('name')} ({m.get('guid')})")
            if len(hits) > 5:
                print(f"  ... +{len(hits)-5} more")
        else:
            print(f"'{s}': 0 monitors")

    print(f"\nWrote detailed results to: {OUTPUT_CSV} (rows: {total_hits})")
    print("Done.")

if __name__ == "__main__":
    main()