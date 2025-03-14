"""
     Who: Juan Sidberry
    When: 2024-02-12
 Updated: 2024-06-17
     Why: Explore (POC) using code to query New Relic's GraphQL API.
    What: This script will list all infrastructure agents deployed in your New Relic account.
"""
import requests
import json
import os
import csv
import pprint as pp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NR_API_KEY')

# Define the URL
URL = "https://api.newrelic.com/graphql"

# Define the headers
HEADERS = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}

OUTPUT_FILE = "list-apm-agent.csv"


def convert_epoch_to_formatted_date(epoch):
    # Convert the epoch from milliseconds to seconds
    epoch_in_seconds = epoch / 1000.0

    # Convert the epoch to datetime object
    dt_object = datetime.fromtimestamp(epoch_in_seconds)
    
    # Format the datetime object to "YYYY/MM/DD HH:MM:SS"
    # formatted_date = dt_object.strftime("%Y/%m/%d %H:%M:%S")
    formatted_date = dt_object.strftime("%Y/%m/%d")
    
    return formatted_date


def fetch_apm_agents(cursor=None):
    query = """
    {
      actor {
        entitySearch(queryBuilder: {type: APPLICATION}) {
          results {
            entities {
              name
              ... on ApmApplicationEntityOutline {
                reporting
                language
                runningAgentVersions {
                  maxVersion
                  minVersion
                }
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
    account(id: 837777) {
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
    """

    if cursor:
        query = query.replace('policiesSearch', f'policiesSearch(cursor: "{cursor}")')
    
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    return response.json()


def fetch_synthetic_monitors(cursor):
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


def get_all_apm_agents():
    output_file = 'list-apm-agent.csv'
    apm_agents = []
    cursor = None
    
    while True:
        data = fetch_apm_agents(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        apm_agents.extend(entities)
        
        cursor = data['data']['actor']['entitySearch']['results']['nextCursor']
        if not cursor:
            break
    
    # return apm_agents
    
    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","reporting","language","max_version","min_version"])
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

            writer.writerow([agent['name'],reporting,language,max_version,min_version])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_dashboard_data():
    output_file = 'list-dashboards.csv'
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


def get_all_infra_agents():
    output_file = 'list-infra-agents.csv'
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
    output_file = 'list-policies.csv'
    policies = []
    cursor = None
    
    while True:
        data = fetch_policies(cursor)
        entities = data['data']['actor']['account']['alerts']['policiesSearch']['policies']
        policies.extend(entities)

        cursor = data['data']['actor']['account']['alerts']['policiesSearch']['nextCursor']
        if not cursor:
            break

    # return policies

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","id","accountId",])
        for policy in policies:
            writer.writerow([
                policy['name'],
                policy['id'],
                policy['accountId']
            ])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_synthetic_monitors():
    output_file = 'list-synthetic-monitors.csv'
    synthetic_monitors = []
    cursor = None
    
    while True:
        data = fetch_synthetic_monitors(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        synthetic_monitors.extend(entities)
        
        cursor = data['data']['actor']['entitySearch']['results']['nextCursor']
        if not cursor:
            break
    
    # return synthetic_monitors

    with open(output_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["name","accountId","entityType","lastReportingChangeAt","status","monitorType","monitoredUrl","period","reporting","permalink"])
        for monitor in synthetic_monitors:
            writer.writerow([
                monitor['name'],
                monitor['accountId'],
                monitor['entityType'],
                convert_epoch_to_formatted_date(monitor['lastReportingChangeAt']),
                monitor['monitorSummary']['status'],
                monitor['monitorType'],
                monitor['monitoredUrl'],
                monitor['period'],
                monitor['reporting'],
                monitor['permalink']
            ])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def get_all_users():
    output_file = 'list-users.csv'
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
        writer.writerow(["email","name"])
        for useraccount in useraccounts:
            writer.writerow([
                useraccount['email'],
                useraccount['name']
            ])

    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')


def main():
    get_all_apm_agents()
    get_all_dashboard_data()
    get_all_infra_agents()
    get_all_policies()
    get_all_synthetic_monitors()
    get_all_users()
    
    # apm_agents         = get_all_apm_agents()
    # dashboard_data     = get_all_dashboard_data()
    # infra_agents       = get_all_infra_agents()
    # synthetic_monitors = get_all_synthetic_monitors()

if __name__ == '__main__':
    main()