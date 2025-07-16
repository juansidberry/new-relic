import requests
import json
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

API_KEY = os.getenv('NR_API_KEY')
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

GRAPHQL_URL = "https://api.newrelic.com/graphql"
REST_URL = "https://api.newrelic.com/v2"

HEADERS_GRAPHQL = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}

HEADERS_REST = {
    "Api-Key": API_KEY
}

TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
OUTPUT_FILE = f"{TIMESTAMP}-alert-policies-detailed.csv"


def graphql_query(query):
    response = requests.post(GRAPHQL_URL, headers=HEADERS_GRAPHQL, json={'query': query})
    response.raise_for_status()
    return response.json()


def rest_get(endpoint):
    url = f"{REST_URL}/{endpoint}"
    response = requests.get(url, headers=HEADERS_REST)

    if response.status_code != 200:
        print(f"❌ Error {response.status_code} for endpoint: {url}")
        print("Response text:", response.text)
        response.raise_for_status()

    try:
        return response.json()
    except json.JSONDecodeError:
        print(f"❌ Failed to decode JSON from endpoint: {url}")
        print("Raw response:", response.text)
        raise


def fetch_alert_policies():
    policies = []
    cursor = None

    while True:
        query = f"""
        {{
          actor {{
            account(id: {ACCOUNT_ID}) {{
              alerts {{
                policiesSearch{f'(cursor: \\"{cursor}\\")' if cursor else ''} {{
                  policies {{
                    id
                    name
                    incidentPreference
                  }}
                  nextCursor
                }}
              }}
            }}
          }}
        }}
        """
        data = graphql_query(query)
        result = data['data']['actor']['account']['alerts']['policiesSearch']
        policies.extend(result['policies'])
        cursor = result['nextCursor']
        if not cursor:
            break

    return policies


def fetch_conditions(policy_id):
    all_conditions = []

    endpoints = [
        f"alerts_conditions/policies/{policy_id}.json",
        f"alerts_nrql_conditions/policies/{policy_id}.json",
        f"alerts_plugins_conditions/policies/{policy_id}.json",
        f"alerts_external_service_conditions/policies/{policy_id}.json",
        f"alerts_synthetics_conditions/policies/{policy_id}.json",
        f"alerts_infrastructure_conditions/policies/{policy_id}.json"
    ]

    for endpoint in endpoints:
        try:
            data = rest_get(endpoint)
            for key in data:
                if isinstance(data[key], list):
                    all_conditions.extend(data[key])
        except Exception as e:
            print(f"Error fetching conditions for policy {policy_id}: {e}")

    return all_conditions


def fetch_policy_channel_links(policy_id):
    try:
        data = rest_get(f"alerts_policy_channels.json?policy_id={policy_id}")
        return data.get("channels", [])
    except Exception as e:
        print(f"Error fetching channels for policy {policy_id}: {e}")
        return []


def write_to_csv(filename, rows):
    headers = set()
    for row in rows:
        headers.update(row.keys())

    headers = list(headers)
    if 'id' in headers:
        headers.remove('id')
        headers.insert(0, 'id')
    if 'name' in headers:
        headers.remove('name')
        headers.insert(1, 'name')

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def flatten_conditions(conditions):
    return "; ".join([f"{c.get('type', 'unknown')} - {c.get('name', '')}" for c in conditions])


def flatten_channels(channels):
    return "; ".join([f"{c.get('type')} - {c.get('name')}" for c in channels])


def main():
    print("Fetching alert policies...")
    policies = fetch_alert_policies()

    print("Fetching conditions and channels per policy...")
    output_rows = []
    for policy in policies:
        pid = policy['id']
        conditions = fetch_conditions(pid)
        channels = fetch_policy_channel_links(pid)

        row = {
            'id': pid,
            'name': policy['name'],
            'incidentPreference': policy.get('incidentPreference'),
            'conditions': flatten_conditions(conditions),
            'notification_channels': flatten_channels(channels)
        }
        output_rows.append(row)

    write_to_csv(OUTPUT_FILE, output_rows)
    print(f"\n✅ Done! Output saved to: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    main()

