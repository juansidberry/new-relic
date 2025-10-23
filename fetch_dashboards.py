import requests
import json
import csv
from datetime import datetime
import pprint as pp
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Replace with your New Relic API key
API_KEY      = os.getenv('NR_API_KEY')
ACCOUNT_ID   = os.getenv('ACCOUNT_ID')
HEADERS      = {'Api-Key': API_KEY, 'Content-Type': 'application/json'}
URL          = 'https://api.newrelic.com/graphql'
TIMESTAMP    = datetime.now().strftime("%Y%m%d-%H%M%S")

# GraphQL query to fetch dashboards
QUERY = """
{
  actor {
    entitySearch(query: "type='DASHBOARD'") {
      results {
        entities {
          ... on DashboardEntitiyOutline {
            name
            accountId
            owner { email }
            createdAt
            updatedAt
            lastReportingChangeAt
            permalink
            guid
            tags {
              key
              values
            }
          }
        }
      }
    }
  }
}
"""

# Function to send GraphQL request
def fetch_dashboards():
    headers = {
        "Content-Type": "application/json",
        "API-Key": API_KEY
    }
    
    response = requests.post(URL, json={"query": QUERY}, headers=headers)
    response.raise_for_status()  # Raise error for failed requests
    
    data = response.json()
    return data["data"]["actor"]["entitySearch"]["results"]["entities"]

# Function to write dashboards to CSV
def save_to_csv(dashboards, filename="new_relic_dashboards.csv"):
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(["GUID", "Name", "Account ID", "Permalink", "Tags"])
        
        # Write each dashboard's details
        for dashboard in dashboards:
            tags = "; ".join([f"{tag['key']}={','.join(tag['values'])}" for tag in dashboard.get("tags", [])])
            writer.writerow([dashboard["guid"], dashboard["name"], dashboard["accountId"], dashboard["permalink"], tags])

# Main execution
if __name__ == "__main__":
    dashboards = fetch_dashboards()
    save_to_csv(dashboards)
    print(f"Dashboard data saved to new_relic_dashboards.csv")