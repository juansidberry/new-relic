import requests
import json
import csv
import os
import pprint as pp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access variables using os.getenv
API_KEY    = os.getenv('NR_API_KEY')
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# New Relic GraphQL endpoint
URL = 'https://api.newrelic.com/graphql'

# Define the headers
HEADERS = {
    'Content-Type': 'application/json',
    'API-Key': API_KEY
}

def list_workflows():
    # GraphQL query to list workflows with Webhook destinations
    query = """
    {
      actor {
        account(id: %s) {
          aiWorkflows {
            workflows(filters: {destinationType: WEBHOOK}) {
              entities {
                id
                name
                workflowEnabled
                destinationConfigurations {
                  channelId
                  name
                  type
                  notificationTriggers
                }
                enrichments {
                  configurations {
                    ... on AiWorkflowsNrqlConfiguration {
                      query
                    }
                  }
                  id
                  name
                }
              }
              nextCursor
              totalCount
            }
          }
        }
      }
    }
    """ % ACCOUNT_ID

    # Make the API request
    response = requests.post(URL, headers=HEADERS, json={'query': query})

    # Check if the request was successful
    if response.status_code == 200:
        workflows = response.json()['data']['actor']['account']['aiWorkflows']['workflows']['entities']
        
        # Define the CSV file name
        csv_file = 'workflows_with_webhooks.csv'
        
        # Get the header from the keys of the first dictionary
        if workflows:
            header = workflows[0].keys()
            
            # Write data to CSV file
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(workflows)
            
            print(f"Workflows with Webhook destinations have been written to {csv_file}.")
        else:
            print("No workflows with Webhook destinations found.")
    else:
        print(f"Failed to retrieve workflows: {response.status_code}")

