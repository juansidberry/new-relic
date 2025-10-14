import requests
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# loads values from an environment-varaibles (.env) file 
load_dotenv(override=True)

# Replace with your New Relic API key
API_KEY    = os.getenv('NR_API_KEY')
HEADERS    = { "Api-Key": API_KEY, "Content-Type": "application/json" }
TIMESTAMP  = datetime.now().strftime("%Y%m%d-%H%M%S")
API_URL    = 'https://api.newrelic.com/graphql'


def get_workflows(account_id='837777'):
    print(f"get_workflows for account {account_id}")
    # GraphQL query to retrieve workflows
    query = '''
{
  actor {
    account(id: %s) {
      aiWorkflows {
        workflows {
          entities {
            name
            lastRun
            workflowEnabled
            destinationsEnabled
            updatedAt
            destinationConfigurations {
              channelId
              name
              notificationTriggers
              type
            }
          }
        }
      }
    }
  }
}
''' % account_id
    
    response = requests.post(API_URL, headers=HEADERS, json={'query': query})
    
    if response.status_code == 200:
        data = response.json()
        workflows = data['data']['actor']['account']['aiWorkflows']['workflows']['entities']
        return workflows
    else:
        raise Exception(f"Failed to retrieve workflows: {response.status_code} {response.text}")

def format_workflows(workflows):
    print(f"format_workflows")
    formatted_workflows = []

    for workflow in workflows:
        for destinations in range(len(workflow['destinationConfigurations'])):
            results = {
                'channelId': workflow['destinationConfigurations'][destinations]['channelId'],
                'destinationName': workflow['destinationConfigurations'][destinations]['name'],
                'notificationTriggers': workflow['destinationConfigurations'][destinations]['notificationTriggers'],
                'destinationType': workflow['destinationConfigurations'][destinations]['type'],
                'destinationsEnabled': workflow['destinationsEnabled'],
                'workflowName': workflow['name'],
                'lastRun': workflow['lastRun'],
                'workflowEnabled': workflow['workflowEnabled'],
                'updatedAt': workflow['updatedAt'],
                'accountId': workflow['accountId']
            }
            formatted_workflows.append(results)

    return formatted_workflows

def save_to_csv(formatted_workflows, filename='workflows'):
    print(f"save_to_csv")
    with open(f"{filename}_{TIMESTAMP}.csv", mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            'accountId',
            'workflowName', 
            'workflowEnabled', 
            'lastRun', 
            'updatedAt', 
            'channelId',
            'destinationsEnabled', 
            'destinationName', 
            'destinationType', 
            'notificationTriggers', 
        ])
        
        for workflow in formatted_workflows:
            writer.writerow([
                workflow['accountId'], 
                workflow['workflowName'], 
                workflow['workflowEnabled'], 
                workflow['lastRun'],
                workflow['updatedAt'], 
                workflow['channelId'], 
                workflow['destinationsEnabled'], 
                workflow['destinationName'], 
                workflow['destinationType'], 
                workflow['notificationTriggers'], 
            ])

def main():
    try:
        # contains a query that pulls data from New Relic
        output_filename = 'workflows'
        workflows = []

        for account_id in ['837777','2096527']:
            results = get_workflows(account_id)
            if not results:
                print("No workflows found.")
                return
            else:
                for item in results:
                    item['accountId'] = account_id
                    workflows.append(item)

        # converts raw data to a format that can used in an CSV file
        formatted_workflows = format_workflows(workflows)

        # puts data into CSV format and file
        save_to_csv(formatted_workflows, output_filename)
        print(f"{output_filename}_{TIMESTAMP}.csv")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
