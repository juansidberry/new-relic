"""
     Who: Dalton Robertson
    When: 2024-07-02
     Why: Explore (POC) using code to query New Relic's GraphQL API.
    What: This script will list all users in  New Relic.
"""
import requests
import json
import pprint as pp
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access variables using os.getenv
API_KEY = os.getenv('NR_API_KEY')

# Define the GraphQL endpoint
URL = 'https://api.newrelic.com/graphql'

# Define the headers
headers = {
    'Content-Type': 'application/json',
    'API-Key': API_KEY
}

# loop through the results and print the name of each user
def print_user_details(users):
  results = []
  for user in users['data']['actor']['users']['userSearch']['users']:
      results.append(user)

  return results


def main():
    # Define the GraphQL query
    query = """
    {
      actor {
        users {
          userSearch {
            users {
              name
              email
            }
            nextCursor
          }
        }
      }
    }
    """

    # Make the request
    response = requests.post(URL, headers=headers, json={'query': query})

    # Print the response
    data = json.loads(json.dumps(response.json()))

    results = print_user_details(data)

    for result in results:
       print(result)


if __name__ in '__main__':
   main()