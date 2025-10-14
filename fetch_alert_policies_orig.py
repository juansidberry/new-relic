import requests
import json
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

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


def convert_epoch_to_formatted_date(epoch):
    # Convert the epoch from milliseconds to seconds
    epoch_in_seconds = epoch / 1000.0

    # Convert the epoch to datetime object
    dt_object = datetime.fromtimestamp(epoch_in_seconds)
    
    # Format the datetime object to "YYYY/MM/DD HH:MM:SS"
    formatted_date = dt_object.strftime("%Y-%m-%d")
    
    return formatted_date


def write_to_csv(filename, rows):
    # filename=f'{type}-{TIMESTAMP}.csv'

    # Get all unique keys from all monitors to use as headers
    headers = set()
    for row in rows:
        headers.update(row.keys())

    # Convert headers to a list and reorder "name" first and "url" last
    headers = list(headers)

    if 'id' in headers:
        headers.remove('id')
        headers.insert(0, 'id')
    if 'name' in headers:
        headers.remove('name')
        headers.insert(1, 'name')
    if 'updatedAt' in headers:
        headers.remove('updatedAt')
        headers.append('updatedAt')
    if 'runbookUrl' in headers:
        headers.remove('runbookUrl')
        headers.append('runbookUrl')
    if 'guid' in headers:
        headers.remove('guid')
        headers.append('guid')
    
    # Write to CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            if row.get('updatedAt') is not None and filename not in (f'{TIMESTAMP}-destinations.csv',f'{TIMESTAMP}-workflows.csv'):
                row['updatedAt'] = convert_epoch_to_formatted_date(row['updatedAt'])
                writer.writerow(row)
            else:
                # row['updatedAt'] = convert_epoch_to_formatted_date(row['updatedAt'])
                writer.writerow(row)


def fetch_policies(cursor=None):
    #WIP - condition to find policy/alert relations?
    query = """
{
  actor {
    account(id: %s) {
      alerts {
        policiesSearch {
          policies {
            name
            id
            accountId
          }
          nextCursor
        }
      }
    }
  }
}
    """ % ACCOUNT_ID

    if cursor:
        query = query.replace('policiesSearch', f'policiesSearch(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def get_all_policies(): 
  #WIP
    output_file = f'{TIMESTAMP}-alert-policies.csv'
    results = []
    cursor = None
    
    while True:
        data = fetch_policies(cursor)
        entities = data['data']['actor']['account']['alerts']['policiesSearch']['policies']
        results.extend(entities)

        cursor = data['data']['actor']['account']['alerts']['policiesSearch']['nextCursor']
        if not cursor:
            break

    # write output from above into CSV file 
    write_to_csv(output_file, results)

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')

    return results

get_all_policies()