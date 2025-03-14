"""
     Who: Juan Sidberry
    When: 2024-02-12
 Updated: 2024-07-01
     Why: Explore (POC) using code to query New Relic's GraphQL API.
    What: This script will list all infrastructure agents deployed in your New Relic account.
"""
import requests
import json
import os
import pprint as pp
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NR_API_KEY')

# Define the URL
url = "https://api.newrelic.com/graphql"

# Define the headers
headers = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}

query = """
{
  actor {
    account(id: 837777) {
      nrql(query: "SELECT agentName,agentVersion,entityGuid,entityId,entityKey,entityName,fullHostname,hostStatus,hostname,instanceType,linuxDistribution,operatingSystem,regionName,subscriptionId,tags.environment FROM SystemSample WHERE agentName = 'Infrastructure' SINCE 1 day ago LIMIT MAX") {
        results
      }
    }
  }
}
"""

#  {'agentName','agentVersion','entityGuid','entityId','entityKey','entityName','fullHostname','hostStatus','hostname','instanceType','linuxDistribution','operatingSystem','regionName','subscriptionId', 'tags.environment'}

# Send the request
response = requests.post(url, headers=headers, data=json.dumps({"query": query}))

# Parse the response
data = response.json()

results = []

# Extract the entities
entities = data['data']['actor']['account']['nrql']['results']


# Filter the entities that have a version greater than 1.52.3
filtered_entities = [entity for entity in entities if entity["agentVersion"] != "1.52.3"]

# row_num = 1
# entity_set = set()
# for entity in filtered_entities: #set_entities:
#     results.append([entity['hostname'], entity['agentVersion']])
#     row_num += 1
# thing = results.sort()

# print(len(filtered_entities))
count = 0
frozenset_set = set(frozenset(d.items()) for d in entities)
unique_entities = [dict(fs) for fs in frozenset_set]
with open('nr-infra-agents-list.csv', 'w') as f:
    # final_list = []
    dup_entities = []
    for entity in unique_entities:
        dup_entities.append(entity)
    # using pipe-delimiting as some of the values have comma in them
    # must implement CSV module that will automatically handle commas in values
    f.write(f"count|agentName|agentVersion|fullHostname|hostname|hostStatus|instanceType|linuxDistribution|operatingSystem\n")
    for entity in unique_entities:
        e_count = 0
        for d_entity in dup_entities:
            if d_entity == entity:
                e_count += 1
              
        count += 1
        pp.pprint(entity)
        # final_list.append(entity)
        f.write(f"{count}|{entity['agentName']}|{entity['agentVersion']}|{entity['fullHostname']}|{entity['hostname']}|{entity['hostStatus']}|{entity['instanceType']}|{entity['linuxDistribution']}|{entity['operatingSystem']}\n")


# debug
print(type(entities))
# print(data['data']['actor']['account']['nrql']['results'])
# print(entities)
