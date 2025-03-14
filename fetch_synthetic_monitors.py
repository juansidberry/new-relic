import requests
import json
import csv
import datetime
import pprint as pp
import os
import pandas as pd
from openpyxl import Workbook
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Replace with your New Relic API key
API_KEY      = os.getenv('NR_API_KEY')
ACCOUNT_ID   = os.getenv('ACCOUNT_ID')
HEADERS      = {'Api-Key': API_KEY, 'Content-Type': 'application/json'}
URL          = 'https://api.newrelic.com/graphql'
TIMESTAMP    = datetime.now().strftime("%Y%m%d-%H%M%S")
OUTPUT_FILE_NAME = 'synthetic-monitors'


def convert_epoch_to_formatted_date(epoch):
    # Convert the epoch from milliseconds to seconds
    epoch_in_seconds = epoch / 1000.0

    # Convert the epoch to datetime object
    dt_object = datetime.fromtimestamp(epoch_in_seconds)
    
    # Format the datetime object to "YYYY/MM/DD HH:MM:SS"
    formatted_date = dt_object.strftime("%Y-%m-%d")
    
    return formatted_date

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
    if 'locationFailing' in headers:
        headers.remove('locationFailing')
        headers.insert(1,'locationFailing')
    if 'locationsRunning' in headers:
        headers.remove('locationsRunning')
        headers.insert(2,'locationsRunning')
    if 'status' in headers:
        headers.remove('status')
        headers.insert(3,'status')
    if 'successRate' in headers:
        headers.remove('successRate')
        headers.insert(4,'successRate')
    if 'monitorId' in headers:
        headers.remove('monitorId')
        headers.append('monitorId')
    if 'guid' in headers:
        headers.remove('guid')
        headers.append('guid')
    
    
    # Write to CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for monitor in monitors:
            writer.writerow(monitor)

    # Load the CSV file
    df = pd.read_csv(filename)

    # Calculate the 'monthly_synthetic_count' and add it as a new column
    df['synthetic_count'] = 43200 / df['period']

    # Remove the 'guid' column if it exists
    if 'guid' in df.columns:
        df = df.drop(columns=['guid'])

    # Save the updated DataFrame back to a CSV file
    filename = f"rn_{filename}"
    df.to_csv(filename, index=False)
    # print(f"\nThe following file was created:\n\n\t{filename}\n")

    # Create a new Excel workbook and select the active worksheet
    workbook = Workbook()
    sheet = workbook.active

    # Write the header row to the Excel sheet
    sheet.append(df.columns.tolist()) 

    # Write data to the Excel sheet
    for row in df.itertuples(index=False, name=None):
        sheet.append(row)

    # Add filters to all columns and Freeze the top row
    sheet.auto_filter.ref = sheet.dimensions
    sheet.freeze_panes = 'A2'

    # Save the workbook
    excel_file = f"{filename[:-4]}.xlsx"
    workbook.save(excel_file)
    print(f"\t{excel_file}\n")
    # return filename

    # clean up by rm the .csv files
    os.remove(f"{filename[3:]}")
    os.remove(filename)


def write_monitors_to_excel_file():
    pass

def get_synthetic_data():
    query = """
    {
      actor {
        entitySearch(queryBuilder: {domain: SYNTH, type: MONITOR}) {
          results {
            entities {
              ... on SyntheticMonitorEntityOutline {
                guid
                accountId
                name
                entityType
                lastReportingChangeAt
                monitorId
                monitorType
                period
                reporting
                monitorSummary { status successRate locationsRunning locationsFailing }
                monitoredUrl
                permalink
              }
            }
          }
        }
      }
    }
    """
    monitors = []
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    data = json.loads(json.dumps(response.json()))

    for row in data['data']['actor']['entitySearch']['results']['entities']:
        row['locationsFailing'] = row['monitorSummary']['locationsFailing']
        row['locationsRunning'] = row['monitorSummary']['locationsRunning']
        row['status']           = row['monitorSummary']['status']
        row['successRate']      = row['monitorSummary']['successRate']
        row['lastReportingChangeAt'] = convert_epoch_to_formatted_date(row['lastReportingChangeAt'])
        del row['monitorSummary']
        
        monitors.append(row)

    return monitors


def main():
    # get a list of all data related to synthetics from New Relic
    all_monitors = get_synthetic_data()

    # write output from above into CSV file 
    write_monitors_to_csv(all_monitors)


if __name__ in '__main__':
   main()
   