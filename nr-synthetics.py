import requests
import csv

# New Relic API Key and GraphQL Endpoint
API_KEY = "your_new_relic_api_key"
GRAPHQL_URL = "https://api.newrelic.com/graphql"

# Updated GraphQL Query using queryBuilder and SyntheticMonitorEntityOutline
QUERY = """
{
  actor {
    entitySearch(queryBuilder: {domain: "SYNTH", type: "MONITOR"}) {
      results {
        entities {
          ... on SyntheticMonitorEntityOutline {
            guid
            name
            monitorType
            monitorSummary {
              successRate
              status
              locationsRunning
            }
          }
        }
      }
    }
  }
}
"""

# Headers
HEADERS = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}

# Send request
response = requests.post(GRAPHQL_URL, json={"query": QUERY}, headers=HEADERS)

if response.status_code == 200:
    data = response.json()
    entities = data.get("data", {}).get("actor", {}).get("entitySearch", {}).get("results", {}).get("entities", [])

    # Filter for SCRIPT_BROWSER monitors
    script_browser_monitors = [entity for entity in entities if entity.get("monitorType") == "SCRIPT_BROWSER"]

    # Prepare CSV data
    csv_filename = "synthetic_checks.csv"
    with open(csv_filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Monitor Name", "Success Rate", "Status", "Locations Running"])

        for monitor in script_browser_monitors:
            monitor_name = monitor.get("name", "N/A")
            success_rate = monitor.get("monitorSummary", {}).get("successRate", "N/A")
            status = monitor.get("monitorSummary", {}).get("status", "N/A")
            locations_running = monitor.get("monitorSummary", {}).get("locationsRunning", "N/A")

            writer.writerow([monitor_name, success_rate, status, locations_running])

    print(f"CSV file '{csv_filename}' generated successfully.")
else:
    print(f"Error: {response.status_code}, {response.text}")