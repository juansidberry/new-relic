"""
     Initial Authur: Juan Sidberry
"""
import requests
import json
import csv
import datetime
import pprint as pp
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Replace with your New Relic API key
API_KEY      = os.getenv('NR_API_KEY')
HEADERS      = {'Api-Key': API_KEY, 'Content-Type': 'application/json'}
URL          = 'https://api.newrelic.com/graphql'
TIMESTAMP    = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# loop through the results and print the name of each monitor
def print_destination_names(destinations, search_term):
  results = []
  for destination in destinations['data']['actor']['entitySearch']['results']['entities']:
      if search_term in destination['name']:
         results.append(destination)
  return results


def write_data_to_csv(data, filename=f'alert-destination-{TIMESTAMP}.csv'):
    print(f"\n\trunning write_data_to_csv() function...\n")
    # filename=f'alert-destination-{TIMESTAMP}.csv'

    # Get all unique keys from all data to use as headers
    headers = set()
    for info in data:
        headers.update(info.keys())

    # ensure name is the first column in output
    headers = list(headers)
    if 'name' in headers:
        headers.remove('name')
        headers.insert(0, 'name')
    
    # Write to CSV file
    print(f"\n\tcreating {filename} file...")
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for info in data:
            writer.writerow(info)


def delete_destination(destination_id):
    # GraphQL mutation for deleting a destination
    mutation = '''
    mutation($id: ID!) {
      destinationDelete(id: $id) {
        destination {
          id
        }
      }
    }
    '''

    response = requests.post(URL, headers=HEADERS, json={
        'query': mutation,
        'variables': {'id': destination_id}
    })
    
    if response.status_code == 200:
        result = response.json()
        if 'errors' in result:
            print(f"Error deleting destination {destination_id}: {result['errors']}")
        else:
            print(f"Successfully deleted destination {destination_id}")
    else:
        print(f"Failed to delete destination {destination_id}: {response.status_code}")


def get_all_destination_data():
    print(f"\n\trunning get_all_destination_data() function...\n")
    query = """
    {
      actor {
        entitySearch(query: "type = 'DESTINATION'") {
          results {
            entities {
                guid
                name
                type
                reporting
            }
          }
        }
      }
    }
    """
    destinations = []
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    data = json.loads(json.dumps(response.json()))

    for row in data['data']['actor']['entitySearch']['results']['entities']:
        destinations.append(row)

    return destinations


def main():
    # get a list of all data related to synthetics from New Relic
    all_destinations = get_all_destination_data()

    # write output from above into CSV file 
    write_data_to_csv(all_destinations)


if __name__ in '__main__':
   main()
   