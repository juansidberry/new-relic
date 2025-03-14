import requests
import json
import csv
import datetime
import pprint as pp
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Replace with your New Relic API key
API_KEY      = os.getenv('NR_API_KEY')
ACCOUNT_ID   = os.getenv('ACCOUNT_ID')
HEADERS      = {'Api-Key': API_KEY, 'Content-Type': 'application/json'}
URL          = 'https://api.newrelic.com/graphql'
TIMESTAMP    = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
OUTPUT_FILE_NAME = 'apm-monitors'

# loop through the results and print the name of each monitor
def print_monitor_names(monitors, search_term):
  results = []
  for monitor in monitors['data']['actor']['entitySearch']['results']['entities']:
      if search_term in monitor['name']:
         results.append(monitor)
  return results


def write_monitors_to_csv(monitors):
    filename=f'{OUTPUT_FILE_NAME}-{TIMESTAMP}.csv'

    # Get all unique keys from all monitors to use as headers
    headers = set()
    for monitor in monitors:
        headers.update(monitor.keys())

    # Convert headers to a list and reorder "name" first and "url" last
    headers = list(headers)
    if 'name' in headers:
        headers.remove('name')
        headers.insert(0, 'name')
    if 'url' in headers:
        headers.remove('url')
        headers.append('url')
    
    # Write to CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for monitor in monitors:
            writer.writerow(monitor)
    print(f"\nThe following file was created:\n\n\t{filename}\n")


def get_apm_application_data():
    query = """
{
  actor {
    entitySearch(queryBuilder: {type: APPLICATION, domain: APM}) {
      results {
        entities {
          ... on ApmApplicationEntityOutline {
            guid
            name
            entityType
            runningAgentVersions {
              maxVersion
              minVersion
            }
            type
            reporting
            applicationId
            language
          }
        }
        nextCursor
      }
    }
  }
}
    """
    monitors = []
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    data = json.loads(json.dumps(response.json()))

    for row in data['data']['actor']['entitySearch']['results']['entities']:
        
        monitors.append(row)

    return monitors


def main():
    # get a list of all data related to synthetics from New Relic
    all_monitors = get_apm_application_data()

    # write output from above into CSV file 
    write_monitors_to_csv(all_monitors)


if __name__ in '__main__':
   main()
   