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
OUTPUT_FILE_NAME = 'notification-destination'

# loop through the results and print the name of each monitor
def print_monitor_names(monitors, search_term):
  results = []
  for monitor in monitors['data']['actor']['entitySearch']['results']['entities']:
      if search_term in monitor['name']:
         results.append(monitor)
  return results


def write_to_csv(filename, rows):
    # filename=f'{OUTPUT_FILE_NAME}-{TIMESTAMP}.csv'

    # Get all unique keys from all monitors to use as headers
    headers = set()
    for row in rows:
        headers.update(row.keys())

    # Convert headers to a list and reorder "name" first and "url" last
    headers = list(headers)
    if 'id' in headers:
        headers.remove('id')
        headers.insert(0, 'id')
    if 'guid' in headers:
        headers.remove('guid')
        headers.insert(1, 'guid')
    if 'key' in headers:
        headers.remove('key')
        headers.append('key')
    if 'value' in headers:
        headers.remove('value')
        headers.append('value')
    
    # Write to CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\nThe following file was created:\n\n\t{filename}\n")


def update_notifications(useraccounts, notifications):
    # Create a dictionary to map userId to name
    user_dict = {user['userId']: user['name'] for user in useraccounts}
    
    # Update the 'updatedBy' field in notifications
    for notification in notifications:
        user_id = str(notification['updatedBy'])
        if user_id in user_dict:
            notification['updatedBy'] = user_dict[user_id]
    
    return notifications


def fetch_user_accounts(cursor=None):
    query = """
{
  actor {
    users {
      userSearch {
        users {
          userId
          name
          email
        }
        nextCursor
      }
    }
  }
}
    """

    if cursor:
        query = query.replace('userSearch', f'userSearch(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_notifications(cursor=None):
    query = """
{
  actor {
    account(id: %s) {
      aiNotifications {
        destinations {
          entities {
            active
            guid
            id
            name
            status
            type
            properties {
              displayValue
              key
              label
              value
            }
            updatedBy
          }
          nextCursor
        }
      }
    }
  }
}
""" % ACCOUNT_ID
    
    if cursor:
        query = query.replace('destinations', f'destinations(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()

    # results = []
    # response = requests.post(URL, headers=HEADERS, json={'query': query})
    # data = json.loads(json.dumps(response.json()))

    # for row in data['data']['actor']['account']['aiNotifications']['destinations']['entities']:
    #     results.append(row)

    # transformed_data = []
    # for item in results:
    #     # Identify the key that contains the list of dictionaries
    #     list_key = next(key for key, value in item.items() if isinstance(value, list) and all(isinstance(i, dict) for i in value))
        
    #     # Extract base information
    #     base_info = {k: v for k, v in item.items() if k != list_key}
        
    #     # Combine base information with each dictionary in the list
    #     for sub_item in item[list_key]:
    #         transformed_item = base_info.copy()
    #         transformed_item.update(sub_item)
    #         transformed_data.append(transformed_item)

    # useraccounts = []
    # user_cursor = None
    # while True:
    #     user_data = fetch_user_accounts(user_cursor)
    #     entities = user_data['data']['actor']['users']['userSearch']['users']
    #     useraccounts.extend(entities)
        
    #     user_cursor = user_data['data']['actor']['users']['userSearch']['nextCursor']
    #     if not user_cursor:
    #         break

    # return transformed_data


def get_data():
    output_file = f'{TIMESTAMP}-notification.csv'
    notifications = []
    cursor = None
    
    while True:
        data = fetch_notifications(cursor)
        note_entities = data['data']['actor']['account']['aiNotifications']['destinations']['entities']
        notifications.extend(note_entities)
        
        cursor = data['data']['actor']['account']['aiNotifications']['destinations']['nextCursor']
        if not cursor:
            break
    
    useraccounts = []
    user_cursor = None
    while True:
        user_data = fetch_user_accounts(user_cursor)
        # print(data)
        entities = user_data['data']['actor']['users']['userSearch']['users']
        useraccounts.extend(entities)
        
        user_cursor = user_data['data']['actor']['users']['userSearch']['nextCursor']
        if not user_cursor:
            break

    transformed_data = []
    for notification in notifications:
        # Identify the key that contains the list of dictionaries
        list_key = next(key for key, value in notification.items() if isinstance(value, list) and all(isinstance(i, dict) for i in value))
        
        # Extract base information
        base_info = {k: v for k, v in notification.items() if k != list_key}
        
        # Combine base information with each dictionary in the list
        for note in notification[list_key]:
            transformed_note = base_info.copy()
            transformed_note.update(note)
            transformed_data.append(transformed_note)

    updated_notifications = update_notifications(useraccounts, transformed_data)

    write_to_csv(output_file, updated_notifications)

    # print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def main():
    # get a list of all data related to synthetics from New Relic
    results = get_data()
    # print(results)

    # # write output from above into CSV file 
    # write_to_csv(results)


if __name__ in '__main__':
   main()
   