import requests
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NR_API_KEY')
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

URL = "https://api.newrelic.com/graphql"
HEADERS = {"Content-Type": "application/json", "API-Key": API_KEY}
TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")


def log_function_name(func):
    def wrapper(*args, **kwargs):
        print(f'Running: {func.__name__}')
        return func(*args, **kwargs)
    return wrapper


def convert_epoch_to_date(epoch):
    return datetime.fromtimestamp(epoch / 1000).strftime("%Y-%m-%d") if epoch else None

@log_function_name
def write_csv(filename, data, headers=None):
    if not headers:
        headers = sorted({key for row in data for key in row})
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in data:
            if 'updatedAt' in row:
                row['updatedAt'] = convert_epoch_to_date(row['updatedAt'])
            writer.writerow(row)

@log_function_name
def run_graphql_query(query, filename, cursor=None):
    if cursor:
        if filename == 'alerts':
            query = query.replace('nrqlConditionsSearch', f'nrqlConditionsSearch(cursor: "{cursor}")')
        else:
            query = query.replace('results', f'results(cursor: "{cursor}")')
    response = requests.post(URL, headers=HEADERS, json={'query': query})
    response.raise_for_status()
    return response.json()

@log_function_name
def paginate_query(query, data_path, filename):
    results, cursor = [], None
    while True:
        data = run_graphql_query(query, filename, cursor)
        entities = data
        for key in data_path:
            entities = entities.get(key, {})
        print(entities)
        # results.extend(entities.get('entities', []))
        results.extend(entities)

        ### the part we changed
        if filename == 'alerts':
            cursor = data['data']['actor']['account']['alerts']['nrqlConditionsSearch']['nextCursor']
        else:
            cursor = entities.get('nextCursor')
        ### end of the part we changed

        print(len(entities))
        if not cursor:
            break
    return results

@log_function_name
def fetch_and_save(query, data_path, filename, headers=None):
    data = paginate_query(query, data_path, filename)
    write_csv(f"{TIMESTAMP}-{filename}.csv", data, headers)
    print(f'File saved as "{TIMESTAMP}-{filename}.csv"')

# Queries
APM_QUERY = """
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

DASHBOARD_QUERY = """
{
  actor {
    entitySearch(queryBuilder: {type: DASHBOARD}) {
      results {
        entities {
          name
          accountId
          entityType
          lastReportingChangeAt
          owner { email }
          permissions
          permalink
          reporting
        }
        nextCursor
      }
    }
  }
}
"""

INFRA_QUERY = """
{
  actor {
    entitySearch(queryBuilder: {type: HOST}) {
      results {
        entities {
          name
          accountId
          entityType
          lastReportingChangeAt
          permalink
          reporting
        }
        nextCursor
      }
    }
  }
}
"""

POLICY_QUERY = f"""
{{
  actor {{
    account(id: {ACCOUNT_ID}) {{
      alerts {{
        policiesSearch {{
          policies {{
            name
            id
            accountId
          }}
          nextCursor
        }}
      }}
    }}
  }}
}}
"""

USER_QUERY = """
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

ALERTS_QUERY = """
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


def main():
    # fetch_and_save(APM_QUERY, ['data', 'actor', 'entitySearch', 'results'], "apm-agents", ["name", "reporting", "language", "maxVersion", "minVersion"])
    # fetch_and_save(DASHBOARD_QUERY, ['data', 'actor', 'entitySearch', 'results'], "dashboards")
    # fetch_and_save(INFRA_QUERY, ['data', 'actor', 'entitySearch', 'results'], "infra-agents")
    # fetch_and_save(POLICY_QUERY, ['data', 'actor', 'account', 'alerts', 'policiesSearch'], "policies")
    # fetch_and_save(USER_QUERY, ['data', 'actor', 'users', 'userSearch'], "users")
    fetch_and_save(ALERTS_QUERY, ['data', 'actor', 'account', 'alerts', 'nrqlConditionsSearch', 'nrqlConditions'], "alerts")

if __name__ == "__main__":
    main()