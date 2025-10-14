import requests
import json
import os
import csv
import pprint as pp
from datetime import datetime
from dotenv import load_dotenv
from fetch_synthetic_monitors import get_synthetic_data
from fetch_apm_monitors import get_apm_application_data

load_dotenv(override=True)

API_KEY = os.getenv('NR_API_KEY')
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# Define the URL
URL = "https://api.newrelic.com/graphql"

# Define the headers
HEADERS = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}

OUTPUT_FILE = "list-apm-agent.csv"
TIMESTAMP  = datetime.now().strftime("%Y%m%d-%H%M%S")

def audit_existing_drop_rules():
    # print("Action One selected. (Function not yet implemented)")
    query = """
{
  actor {
    account(id: %s) {
      nrqlDropRules {
        list {
          rules {
            id
            nrql
            accountId
            action
            createdBy
            createdAt
            description
          }
          error {
            reason
            description
          }
        }
      }
    }
  }
}
""" % ACCOUNT_ID
    
    output_file = f'{TIMESTAMP}-drop-rules.csv'
    results = []
    cursor = None

    if cursor:
        query = query.replace('workflows', f'workflows(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def action_two():
    print("Action Two selected. (Function not yet implemented)")

def action_three():
    print("Action Three selected. (Function not yet implemented)")

def show_menu():
    print("\nPlease choose an action:")
    print("1. audit existing drop rules")
    print("2. get existing tags on all entities -> CSV")
    print("3. Action Three")
    print("0. Exit")

def main():
    while True:
        show_menu()
        choice = input("Enter your choice: ")

        if choice == '1':
            results = audit_existing_drop_rules()
            print("\n")
            print(f"Error: {results['data']['actor']['account']['nrqlDropRules']['list']['error']}")
            print(f"Rules: {results['data']['actor']['account']['nrqlDropRules']['list']['rules']}")
            print()
        elif choice == '2':
            action_two()
        elif choice == '3':
            action_three()
        elif choice == '0':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == '__main__':
    main()