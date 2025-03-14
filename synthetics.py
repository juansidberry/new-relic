import requests
import os
import csv
import datetime
import base64
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Replace with your New Relic API key
API_KEY      = os.getenv('NR_API_KEY')
HEADERS      = {'Api-Key': API_KEY, 'Content-Type': 'application/json'}
URL          = 'https://synthetics.newrelic.com/synthetics/api/v3/monitors'
TIMESTAMP    = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
LOC_DIR_NAME = "nr-synthetic-scripts-bkups"


def delete_synthetic(id):
    # Replace with your New Relic API key and monitor ID
    api_key = API_KEY
    monitor_id = id

    # NerdGraph endpoint
    url = 'https://api.newrelic.com/graphql'

    # GraphQL query to delete a synthetic monitor
    query = '''
    mutation {
      syntheticsDeleteMonitor(guid: "''' + monitor_id + '''") {
        errors {
          description
        }
      }
    }
    '''

    response = requests.post(url, json={'query': query}, headers=HEADERS)

    if response.status_code == 200:
        result = response.json()
        print(result)
        # if 'errors' in result['data']['syntheticsDeleteMonitor']:
        #     print("Error deleting monitor:", result['data']['syntheticsDeleteMonitor']['errors'])
        # else:
        #     print("Monitor deleted successfully.")
    else:
        print("Failed to delete monitor. Status code:", response.status_code)




def fetch_all_monitors():
    monitors = []
    offset = 0
    limit = 100  # Number of monitors per page

    while True:
        response = requests.get(f"{URL}?offset={offset}&limit={limit}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            monitors.extend(data.get('monitors', []))
            if len(data.get('monitors', [])) < limit:
                break  # No more pages
            offset += limit
        else:
            print(f"Failed to retrieve monitors: {response.status_code}")
            break

    return monitors


def get_monitor_names():
    monitor_names = []
    offset = 0
    limit = 100  # Number of monitors per page

    while True:
        response = requests.get(f"{URL}?offset={offset}&limit={limit}", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            monitors = data.get('monitors', [])
            monitor_names.extend([monitor['name'] for monitor in monitors])
            if len(monitors) < limit:
                break  # No more pages
            offset += limit
            return monitor_names
        else:
            print(f"Failed to retrieve monitors: {response.status_code}")
            break
    return monitor_names


def write_monitors_to_csv(monitors, filename='synthetic_monitors.csv'):
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


def save_synthetic_scripts(synthetics):
    dir_path = f"{LOC_DIR_NAME}/backup-{TIMESTAMP}"
    loc_dir = Path(dir_path)
    loc_dir.mkdir(parents=True, exist_ok=True)

    for synthetic in synthetics:
        if synthetic['type'] == 'SCRIPT_BROWSER':
            script_response = requests.get(f"{URL}/{synthetic['id']}/script", headers=HEADERS)
            script_response.raise_for_status()
            script = script_response.json()
            script_text = base64.b64decode(script['scriptText'])
            synthetic_name = synthetic['name'].replace(" ", "-")
            filename = loc_dir / f'{synthetic_name}.js'
            # filename.write_text(str(script_text, "utf-8"))
            with open(filename, 'w') as file:
                file.write(str(script_text, "utf-8"))


def find_alert_condition(monitors, monitor_name):
    # Find the monitor with the specified name
    monitor_id = None
    for monitor in monitors:
        if monitor['name'] == monitor_name:
            monitor_id = monitor['id']
            break
        # print(monitor_id)
    if monitor_id:
        # New Relic API endpoint for alert conditions
        # alert_conditions_url = f'https://api.newrelic.com/v2/alerts_synthetics_conditions.json?monitor_id={monitor_id}'
        alert_conditions_url      = f'https://synthetics.newrelic.com/synthetics/api/v3/monitors' # ?monitor_id={monitor_id}'
        alert_conditions_response = requests.get(alert_conditions_url, headers=HEADERS)
        print(alert_conditions_response.json())
        # alert_conditions          = alert_conditions_response.json() # ['synthetics_conditions']


        # print(f"Alert conditions linked to {monitor_name}:")
        # for condition in alert_conditions:
        #     print(condition)
    else:
        print(f"Monitor named {monitor_name} not found.")


# delete_synthetic('68414806-51f0-4ef9-9396-f6bf65fa8b4c')
dir_path = f"{LOC_DIR_NAME}/backup-{TIMESTAMP}"
# # get all synthetic monitor data into CSV file
all_monitors = fetch_all_monitors()

if all_monitors:
    write_monitors_to_csv(all_monitors)
    # save_synthetic_scripts(all_monitors)
    # find_alert_condition(all_monitors, 'CRM_WEB_LOGIN_v2')
    # print(f"All synthetic monitor data has been written to .csv file or {dir_path}")
else:
    print("No synthetic monitors found or failed to retrieve synthetic monitors.")
    
