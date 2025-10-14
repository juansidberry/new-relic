import requests, os, json, datetime
import argparse
from dotenv import load_dotenv

load_dotenv(override=True)
# Replace with your actual values
API_KEY      = os.getenv('NR_API_KEY')
# ACCOUNT_ID   = os.getenv('ACCOUNT_ID')
DESTINATION_ID = "YOUR_DESTINATION_ID"
URL          = 'https://api.newrelic.com/graphql'

# CLI argument parsing
parser = argparse.ArgumentParser(description="Delete a New Relic destination.")
parser.add_argument("--account", required=True, help="New Relic account ID")
args = parser.parse_args()
account_id = args.account

# Headers
headers = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}

# Step 1: Get all destinations
list_query = """
query {
  aiNotificationsDestinations(accountId: %s) {
    destinations {
      id
      name
      type
    }
  }
}
""" % account_id

response = requests.post(URL, json={"query": list_query}, headers=headers)
destinations = response.json().get("data", {}).get("aiNotificationsDestinations", {}).get("destinations", [])

if not destinations:
    print("No destinations found.")
    exit()

# Step 2: Display destinations and prompt user to choose one
print("Available destinations:")
for i, dest in enumerate(destinations):
    print(f"{i + 1}. {dest['name']} (ID: {dest['id']}, Type: {dest['type']})")

choice = int(input("Enter the number of the destination to delete: ")) - 1
if choice < 0 or choice >= len(destinations):
    print("Invalid selection.")
    exit()

destination_id = destinations[choice]["id"]

# Step 3: Delete the selected destination
delete_mutation = """
mutation {
  aiNotificationsDeleteDestination(
    accountId: %s
    destinationId: "%s"
  ) {
    ids
    error {
      details
    }
  }
}
""" % (account_id, destination_id)

delete_response = requests.post(URL, json={"query": delete_mutation}, headers=headers)
result = delete_response.json().get("data", {}).get("aiNotificationsDeleteDestination", {})

if result.get("error"):
    print("Error deleting destination:", result["error"]["details"])
else:
    print("Successfully deleted destination. IDs:", result["ids"])
