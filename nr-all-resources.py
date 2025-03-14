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


def update_destinations(useraccounts, destinations):
    # Create a dictionary to map userId to name
    user_dict = {user['userId']: user['name'] for user in useraccounts}
    
    # Update the 'updatedBy' field in destinations
    for destination in destinations:
        user_id = str(destination['updatedBy'])
        if user_id in user_dict:
            destination['updatedBy'] = user_dict[user_id]
    
    return destinations


def fetch_apm_agents(cursor=None):
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

    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_dashboard_data(cursor=None):
    query = """
    {
      actor {
        entitySearch(queryBuilder: {type: DASHBOARD}) {
          results {
            entities {
              ... on DashboardEntityOutline {
                name
                accountId
                entityType
                lastReportingChangeAt
                owner { email }
                permissions
                permalink
                reporting
              }
            }
            nextCursor
          }
        }
      }
    }
    """

    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_infra_agents(cursor=None):
    query = """
    {
      actor {
        entitySearch(queryBuilder: {type: HOST}) {
          results {
            entities {
              ... on InfrastructureHostEntityOutline {
                name
                accountId
                entityType
                lastReportingChangeAt
                permalink
                reporting
              }
            }
            nextCursor
          }
        }
      }
    }
    """

    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


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


def fetch_workflows(cursor=None):
    query = """
{
  actor {
    account(id: %s) {
      aiWorkflows {
        workflows {
          entities {
            name
            updatedAt
            workflowEnabled
            destinationConfigurations {
              channelId
              name
              notificationTriggers
              type
            }
            createdAt
            lastRun
          }
          nextCursor
        }
      }
    }
  }
}
""" % ACCOUNT_ID

    if cursor:
        query = query.replace('workflows', f'workflows(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_synthetics(cursor):
    query = """
    {
      actor {
        entitySearch(queryBuilder: {type: MONITOR}) {
          results {
            entities {
              ... on SyntheticMonitorEntityOutline {
                name
                accountId
                entityType
                lastReportingChangeAt
                monitorId
                monitorSummary { status }
                monitorType
                monitoredUrl
                permalink
                period
                reporting
              }
            }
            nextCursor
          }
        }
      }
    }
    """

    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


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


def fetch_alert_conditions(cursor=None):
    query = """
{
  actor {
    user {
      name
    }
    account(id: %s) {
      alerts {
        nrqlConditionsSearch {
          nrqlConditions {
            id
            name
            policyId
            runbookUrl
            type
            updatedAt
            updatedBy {
              name
            }
          }
          nextCursor
        }
      }
    }
  }
}
    """ % ACCOUNT_ID

    if cursor:
        query = query.replace('nrqlConditionsSearch', f'nrqlConditionsSearch(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_notification_channels(cursor=None):
    query = """
{
  actor {
    account(id: %s) {
      alerts {
        notificationChannels {
          channels {
            associatedPolicies {
              policies {
                id
                name
              }
            }
            id
            name
            type
          }
          nextCursor
        }
      }
    }
  }
} """ % ACCOUNT_ID
    
    if cursor:
        query = query.replace('notificationChannels', f'notificationChannels(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_destinations(cursor=None):
    query = """
{
  actor {
    account(id: %s) {
      aiNotifications {
        destinations {
          entities {
            name
            id
            status
            type
            updatedAt
            updatedBy
            active
            guid
          }
          nextCursor
        }
      }
    }
  }
} """ % ACCOUNT_ID
    
    if cursor:
        query = query.replace('destinations', f'destinations(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def get_all_apm_agents():
    output_file = f'{TIMESTAMP}-list-apm-agent.csv'
    apm_agents = []
    cursor = None
    
    # while True:
    #     data = fetch_apm_agents(cursor)
    #     entities = data['data']['actor']['entitySearch']['results']['entities']
    #     apm_agents.extend(entities)
        
    #     cursor = data['data']['actor']['entitySearch']['results']['nextCursor']
    #     if not cursor:
    #         break
    
    # return apm_agents
    apm_agents = get_apm_application_data()
    
    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","reporting","language","max_version","min_version","entityType","type","applicationId","guid"])
        for agent in apm_agents:
            try:
                reporting = f"{agent['reporting']}"
            except KeyError:
                reporting = f"Unknown"

            try:
                language = f"{agent['language']}"
            except KeyError:
                language = f"Unknown"

            try:
                max_version = agent['runningAgentVersions']['maxVersion']
            except TypeError as e:
                max_version = "None"
            except KeyError:
                max_version = "None"

            try:
                min_version = agent['runningAgentVersions']['minVersion']
            except TypeError as e:
                min_version = "None"
            except KeyError:
                min_version = "None"

            try:
                version = f"Version: \n  MaxVersion: {max_version}\n  MinVersion: {min_version}"
            except KeyError as e:
                version = f"  Version: {e}"


            # version = f"  Version: {agent['runningAgentVersions']}"
            # print(f"Name: {agent['name']}")
            # print(f"Reporting: {reporting}")
            # print(f"Language: {language}")
            # print(f"{version}")
            # print('-' * len(version))

            writer.writerow([agent['name'],reporting,language,max_version,min_version,agent['entityType'],agent['type'],agent['applicationId'],agent['guid']])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_dashboard_data():
    output_file = f'{TIMESTAMP}-list-dashboards.csv'
    dashboards = []
    cursor = None
    
    while True:
        data = fetch_dashboard_data(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        dashboards.extend(entities)
        
        cursor = data['data']['actor']['entitySearch']['results']['nextCursor']
        if not cursor:
            break
    
    # return dashboards

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","accountId","entityType","lastReportingChangeAt","owner","permissions","reporting","permalink"])
        for dashboard in dashboards:
            # try:
            #     reporting = f"{dashboard['reporting']}"
            # except KeyError:
            #     reporting = f"Unknown"

            writer.writerow([
                dashboard['name'],
                dashboard['accountId'],
                dashboard['entityType'],
                convert_epoch_to_formatted_date(dashboard['lastReportingChangeAt']),
                dashboard['owner'],
                dashboard['permissions'],
                dashboard['reporting'],
                dashboard['permalink']
            ])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_destinations(users=None): 
  #WIP
    output_file = f'{TIMESTAMP}-destinations.csv'
    results = []
    cursor = None
    
    while True:
        data = fetch_destinations(cursor)
        # print(data)
        entities = data['data']['actor']['account']['aiNotifications']['destinations']['entities']
        results.extend(entities)

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

    updated_destinations = update_destinations(useraccounts, results)

    # write output from above into CSV file 
    write_to_csv(output_file, updated_destinations)

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')

    return results


def get_all_infra_agents():
    output_file = f'{TIMESTAMP}-list-infra-agents.csv'
    infra_agents = []
    cursor = None
    
    while True:
        data = fetch_infra_agents(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        infra_agents.extend(entities)
        
        cursor = data['data']['actor']['entitySearch']['results']['nextCursor']
        if not cursor:
            break
    
    # return infra_agents

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","accountId","entityType","lastReportingChangeAt","reporting","permalink"])
        for infra_agent in infra_agents:
            try:
                writer.writerow([
                    infra_agent['name'],
                    infra_agent['accountId'],
                    infra_agent['entityType'],
                    convert_epoch_to_formatted_date(infra_agent['lastReportingChangeAt']),
                    infra_agent['reporting'],
                    infra_agent['permalink']
                ])
            except KeyError:
                pass

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


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


def get_all_workflows(): 
  #WIP
    output_file = f'{TIMESTAMP}-workflows.csv'
    results = []
    cursor = None
    
    while True:
        data = fetch_workflows(cursor)
        entities = data['data']['actor']['account']['aiWorkflows']['workflows']['entities']
        results.extend(entities)

        cursor = data['data']['actor']['account']['aiWorkflows']['workflows']['nextCursor']
        if not cursor:
            break
        
    transformed_data = []
    for workflow in results:
        # Identify the key that contains the list of dictionaries
        list_key = next(key for key, value in workflow.items() if isinstance(value, list) and all(isinstance(i, dict) for i in value))
        
        # Extract base information
        base_info = {k: v for k, v in workflow.items() if k != list_key}
        
        # Combine base information with each dictionary in the list
        for note in workflow[list_key]:
            print(note)
            note['channelName'] = note['name']
            del note['name']
            transformed_note = base_info.copy()
            transformed_note.update(note)
            transformed_data.append(transformed_note)

    # write output from above into CSV file 
    write_to_csv(output_file, transformed_data)

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')

    return results


def get_all_alert_conditions(policies=None):
    output_file = f'{TIMESTAMP}-alert-conditions.csv'
    results = []
    cursor = None
    
    while True:
        data = fetch_alert_conditions(cursor)
        entities = data['data']['actor']['account']['alerts']['nrqlConditionsSearch']['nrqlConditions']
        results.extend(entities)

        cursor = data['data']['actor']['account']['alerts']['nrqlConditionsSearch']['nextCursor']
        if not cursor:
            break

    if policies:
        for row in results:
            for policy in policies:
                if row['policyId'] == policy['id']:
                    row['policyName'] = policy['name']
        write_to_csv(output_file, results)
    else:
        # write output from above into CSV file 
        write_to_csv(output_file, results)

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_synthetic_monitors():
    output_file = f'{TIMESTAMP}-list-synthetic-monitors.csv'
    synthetic_monitors = []
    cursor = None
    
    # while True:
    #     data = fetch_synthetics(cursor)
    #     entities = data['data']['actor']['entitySearch']['results']['entities']
    #     synthetic_monitors.extend(entities)
        
    #     cursor = data['data']['actor']['entitySearch']['results']['nextCursor']
    #     if not cursor:
    #         break
    
    # # return synthetic_monitors
    synthetic_monitors = get_synthetic_data()
    

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","locationsFailing","locationsRunning","status","successRate","period","accountId","entityType","reporting","monitorType","lastReportingChangeAt","monitoredUrl","permalink"])
        for monitor in synthetic_monitors:
            writer.writerow([
                monitor['name'],
                monitor['locationsFailing'],
                monitor['locationsRunning'],
                monitor['status'],
                monitor['successRate'],
                monitor['period'],
                monitor['accountId'],
                monitor['entityType'],
                monitor['reporting'],
                monitor['monitorType'],
                convert_epoch_to_formatted_date(monitor['lastReportingChangeAt']),
                monitor['monitoredUrl'],
                monitor['permalink']
            ])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_users():
    output_file = f'{TIMESTAMP}-list-users.csv'
    useraccounts = []
    cursor = None
    
    while True:
        data = fetch_user_accounts(cursor)
        entities = data['data']['actor']['users']['userSearch']['users']
        useraccounts.extend(entities)
        
        cursor = data['data']['actor']['users']['userSearch']['nextCursor']
        if not cursor:
            break
    
    # return users

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["id","email","name"])
        for useraccount in useraccounts:
            writer.writerow([
                useraccount['userId'],
                useraccount['email'],
                useraccount['name']
            ])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_notification_channels():
    output_file = f'{TIMESTAMP}-notification-channels.csv'
    results = []
    cursor = None
    
    while True:
        data = fetch_notification_channels(cursor)
        results = data['data']['actor']['account']['alerts']['notificationChannels']['channels']
        results.extend(results)
        
        cursor = data['data']['actor']['account']['alerts']['notificationChannels']['nextCursor']
        if not cursor:
            break
    
    # return users

    write_to_csv(output_file, results)

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def main():
    # get_all_apm_agents()
    # get_all_dashboard_data()
    # get_all_infra_agents()
    # get_all_policies()
    # get_all_synthetic_monitors()
    # get_all_users()
    # get_all_notification_channels()
    # get_all_destinations()
    get_all_workflows()
    # get_all_alert_conditions(get_all_policies())
    
    # apm_agents   = get_all_apm_agents()
    # dashboards   = get_all_dashboard_data()
    # infra_agents = get_all_infra_agents()
    # synthetics   = get_all_synthetic_monitors()
    # policies     = get_all_policies()
    # users        = get_all_users()
    # destinations = get_all_destinations()
    # print(policies)

if __name__ == '__main__':
    main()