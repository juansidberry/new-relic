import argparse
import csv
import json
import os
import re
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('NR_API_KEY') or os.getenv('NEW_RELIC_USER_KEY') or os.getenv('NEW_RELIC_API_KEY')
# Back-compat: script historically used ACCOUNT_ID env var for single-account operations
ENV_ACCOUNT_ID = os.getenv('ACCOUNT_ID')

URL = "https://api.newrelic.com/graphql"
HEADERS = {"Content-Type": "application/json", "API-Key": API_KEY}
TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")

# -----------------------------
# Utility helpers
# -----------------------------

def require_api_key():
    if not API_KEY:
        raise RuntimeError("Missing API key. Set NR_API_KEY (or NEW_RELIC_USER_KEY) environment variable.")

def convert_epoch_to_formatted_date(epoch):
    # Convert the epoch from milliseconds to seconds
    epoch_in_seconds = epoch / 1000.0
    dt_object = datetime.fromtimestamp(epoch_in_seconds)
    return dt_object.strftime("%Y-%m-%d")


def write_csv(filename, rows, field_order=None):
    if not rows:
        print(f"No data to write for {filename}.")
        return
    # Collect union of keys if no explicit header order provided
    keys = field_order or sorted({k for row in rows for k in row.keys()})
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keys})


# -----------------------------
# GraphQL fetchers (Apm, Dashboards, Infra, Synthetics, Users)
# -----------------------------

def fetch_apm_agents(cursor=None):
    query = """
    {
      actor { entitySearch(queryBuilder: {type: APPLICATION}) {
        results { entities {
          name
          ... on ApmApplicationEntityOutline {
            reporting
            language
            runningAgentVersions { maxVersion minVersion }
          }
        }
        nextCursor
      }}
      }
    }
    """
    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


def fetch_dashboard_data(cursor=None):
    query = """
    {
      actor { entitySearch(queryBuilder: {type: DASHBOARD}) {
        results { entities {
          ... on DashboardEntityOutline {
            name accountId entityType lastReportingChangeAt
            owner { email }
            permissions permalink reporting
          }
        }
        nextCursor
      }}
      }
    }
    """
    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


def fetch_infra_agents(cursor=None):
    query = """
    {
      actor { entitySearch(queryBuilder: {type: HOST}) {
        results { entities {
          ... on InfrastructureHostEntityOutline {
            name accountId entityType lastReportingChangeAt permalink reporting
          }
        }
        nextCursor
      }}
      }
    }
    """
    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


def fetch_synthetic_monitors(cursor=None):
    query = """
    {
      actor { entitySearch(queryBuilder: {type: MONITOR}) {
        results { entities {
          ... on SyntheticMonitorEntityOutline {
            name accountId entityType lastReportingChangeAt
            monitorId monitorSummary { status locationsRunning successRate }
            monitorType monitoredUrl period reporting guid type
            tags { key values }
          }
        }
        nextCursor
      }}
      }
    }
    """
    if cursor:
        query = query.replace('results', f'results(cursor: "{cursor}")')
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


def fetch_user_accounts(cursor=None):
    query = """
    {
      actor { users { userSearch {
        users { name email }
        nextCursor
      }}}
    }
    """
    if cursor:
        query = query.replace('userSearch', f'userSearch(cursor: "{cursor}")')
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


# -----------------------------
# Policies & NRQL Conditions (per-account)
# -----------------------------

def fetch_policies(account_id, cursor=None):
    query = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          alerts {{
            policiesSearch{f'(cursor: "{cursor}")' if cursor else ''} {{
              nextCursor
              policies {{ id name incidentPreference }}
            }}
          }}
        }}
      }}
    }}
    """
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


def fetch_alert_conditions(account_id, cursor=None):
    # Expanded to include enabled, nrql{query}, and terms via inline fragments for each NRQL condition subtype
    query = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          alerts {{
            nrqlConditionsSearch{f'(cursor: "{cursor}")' if cursor else ''} {{
              nextCursor
              nrqlConditions {{
                id
                name
                policyId
                runbookUrl
                type
                updatedAt
                updatedBy {{ name }}
                # --- NRQL condition subtypes ---
                ... on AlertsNrqlStaticCondition {{
                  enabled
                  nrql {{ query }}
                  terms {{
                    threshold
                    thresholdDuration
                    thresholdOccurrences
                    operator
                    priority
                  }}
                }}
                ... on AlertsNrqlBaselineCondition {{
                  enabled
                  nrql {{ query }}
                  terms {{
                    threshold
                    thresholdDuration
                    thresholdOccurrences
                    operator
                    priority
                  }}
                  baselineDirection
                }}
                ... on AlertsNrqlOutlierCondition {{
                  enabled
                  nrql {{ query }}
                  terms {{
                    threshold
                    thresholdDuration
                    thresholdOccurrences
                    operator
                    priority
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


# -----------------------------
# AI Notifications Channels (new platform, used by Workflows)
# -----------------------------

def fetch_notification_channels_ai(account_id, cursor=None):
    query = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          aiNotifications {{
            channels{f'(cursor: "{cursor}")' if cursor else ''} {{
              nextCursor
              entities {{ id name type destinationId product }}
            }}
          }}
        }}
      }}
    }}
    """
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


# -----------------------------
# Legacy Alerts Notification Channels (deprecated platform)
# -----------------------------

def fetch_notification_channels_legacy(account_id, cursor=None):
    query = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          alerts {{
            notificationChannels{f'(cursor: "{cursor}")' if cursor else ''} {{
              nextCursor
              channels {{
                id name type
                associatedPolicies {{ policies {{ id name }} }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


# -----------------------------
# Workflows (full objects including issuesFilter and destinationConfigurations)
# -----------------------------

def fetch_workflows_page(account_id, cursor=None):
    query = f"""
    {{
      actor {{
        account(id: {account_id}) {{
          aiWorkflows {{
            workflows(filters: {{}}{f', cursor: "{cursor}"' if cursor else ''}) {{
              nextCursor
              entities {{
                id name workflowEnabled destinationsEnabled lastRun updatedAt
                destinationConfigurations {{ channelId name type notificationTriggers }}
                issuesFilter {{
                  name type
                  predicates {{ attribute operator values }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    return requests.post(URL, headers=HEADERS, json={'query': query}).json()


# -----------------------------
# High-level collectors that iterate accounts and pages
# -----------------------------

def get_all_policies(accounts):
    results = []
    for account_id in accounts:
        cursor = None
        while True:
            data = fetch_policies(account_id, cursor)
            section = data['data']['actor']['account']['alerts']['policiesSearch']
            policies = section['policies']
            for p in policies:
                p['accountId'] = str(account_id)
            results.extend(policies)
            cursor = section.get('nextCursor')
            if not cursor:
                break
    # CSV
    write_csv(f'{TIMESTAMP}-policies.csv', results, field_order=['accountId','id','name','incidentPreference'])
    print(f'\n\n\tPlease see the output file named "{TIMESTAMP}-policies.csv"\n\n')
    return results


def _format_terms(terms):
    """
    Convert a list of term dicts into a compact, human-readable string.
    Example element: priority=CRITICAL operator=ABOVE threshold=13 duration=180s occurrences=ALL
    """
    if not terms:
        return None
    parts = []
    for t in terms:
        if not isinstance(t, dict):
            continue
        frag = []
        if t.get('priority'): frag.append(f"priority={t['priority']}")
        if t.get('operator'): frag.append(f"operator={t['operator']}")
        if 'threshold' in t and t['threshold'] is not None:
            frag.append(f"threshold={t['threshold']}")
        if t.get('thresholdDuration') is not None:
            frag.append(f"duration={t['thresholdDuration']}s")
        if t.get('thresholdOccurrences'):
            frag.append(f"occurrences={t['thresholdOccurrences']}")
        parts.append(" ".join(frag))
    return " | ".join(parts) if parts else None


def get_all_alert_conditions(accounts, policies=None):
    results = []
    for account_id in accounts:
        cursor = None
        while True:
            data = fetch_alert_conditions(account_id, cursor)
            section = data['data']['actor']['account']['alerts']['nrqlConditionsSearch']
            conds = section['nrqlConditions']

            for c in conds:
                c['accountId'] = str(account_id)

                # NEW: nrqlQuery, threshold summary, enabled flag
                nrql = (c.get('nrql') or {})
                c['nrqlQuery'] = nrql.get('query')

                c['threshold'] = _format_terms(c.get('terms'))
                c['enabled'] = c.get('enabled')

                # Format updatedAt (ms epoch) -> "YYYY-MM-DD"
                if c.get('updatedAt') is not None:
                    try:
                        c['updatedAt'] = convert_epoch_to_formatted_date(c['updatedAt'])
                    except Exception:
                        pass

            results.extend(conds)
            cursor = section.get('nextCursor')
            if not cursor:
                break

    # Enrich with policy name if provided
    if policies:
        pol_map = {(str(p['accountId']), str(p['id'])): p['name'] for p in policies}
        for row in results:
            key = (str(row.get('accountId')), str(row.get('policyId')))
            if key in pol_map:
                row['policyName'] = pol_map[key]

    # CSV fields: keep existing + add nrqlQuery, threshold, enabled
    field_order = [
        'accountId', 'id', 'name',
        'policyId', 'policyName',
        'type',
        'enabled',          # NEW
        'nrqlQuery',        # NEW
        'threshold',        # NEW
        'runbookUrl',
        'updatedAt'         # already formatted
    ]
    write_csv(f'{TIMESTAMP}-alert-conditions.csv', results, field_order=field_order)
    print(f'\n\n\tPlease see the output file named "{TIMESTAMP}-alert-conditions.csv"\n\n')
    return results


def get_all_notification_channels_ai(accounts):
    results = []
    for account_id in accounts:
        cursor = None
        while True:
            data = fetch_notification_channels_ai(account_id, cursor)
            section = data['data']['actor']['account']['aiNotifications']['channels']
            entities = section['entities']
            for ch in entities:
                ch['accountId'] = str(account_id)
            results.extend(entities)
            cursor = section.get('nextCursor')
            if not cursor:
                break
    field_order = ['accountId','id','name','type','product','destinationId']
    write_csv(f'{TIMESTAMP}-notification-channels.csv', results, field_order=field_order)
    print(f'\n\n\tPlease see the output file named "{TIMESTAMP}-notification-channels.csv"\n\n')
    return results


def get_all_notification_channels_legacy(accounts):
    results = []
    for account_id in accounts:
        cursor = None
        while True:
            data = fetch_notification_channels_legacy(account_id, cursor)
            section = data['data']['actor']['account']['alerts']['notificationChannels']
            channels = section['channels']
            for ch in channels:
                ch['accountId'] = str(account_id)
            results.extend(channels)
            cursor = section.get('nextCursor')
            if not cursor:
                break
    # No CSV here by default (to avoid confusion with the AI list), but included in Excel.
    return results


def get_all_workflows_full(accounts):
    all_wf = []
    for account_id in accounts:
        cursor = None
        while True:
            data = fetch_workflows_page(account_id, cursor)
            wf_section = data['data']['actor']['account']['aiWorkflows']['workflows']
            entities = wf_section['entities']
            for wf in entities:
                wf['accountId'] = str(account_id)
            all_wf.extend(entities)
            cursor = wf_section.get('nextCursor')
            if not cursor:
                break
    return all_wf


def get_all_workflows_flat_csv(accounts):
    """Flatten workflows to one row per destination for CSV parity with original script."""
    workflows = get_all_workflows_full(accounts)
    rows = []
    for wf in workflows:
        dests = wf.get('destinationConfigurations') or []
        if not dests:
            rows.append({
                'accountId': wf.get('accountId'),
                'workflowId': wf.get('id'),
                'workflowName': wf.get('name'),
                'workflowEnabled': wf.get('workflowEnabled'),
                'lastRun': wf.get('lastRun'),
                'updatedAt': wf.get('updatedAt'),
                'channelId': None,
                'destinationsEnabled': wf.get('destinationsEnabled'),
                'destinationName': None,
                'destinationType': None,
                'notificationTriggers': None,
            })
        for d in dests:
            rows.append({
                'accountId': wf.get('accountId'),
                'workflowId': wf.get('id'),
                'workflowName': wf.get('name'),
                'workflowEnabled': wf.get('workflowEnabled'),
                'lastRun': wf.get('lastRun'),
                'updatedAt': wf.get('updatedAt'),
                'channelId': d.get('channelId'),
                'destinationsEnabled': wf.get('destinationsEnabled'),
                'destinationName': d.get('name'),
                'destinationType': d.get('type'),
                'notificationTriggers': d.get('notificationTriggers'),
            })
    # CSV
    output_file = f'{TIMESTAMP}-workflows.csv'
    field_order = [
        'accountId','workflowId','workflowName','workflowEnabled','lastRun','updatedAt',
        'channelId','destinationsEnabled','destinationName','destinationType','notificationTriggers'
    ]
    write_csv(output_file, rows, field_order)
    print(f'\n\n\tPlease see the output file named "{output_file}"\n\n')
    return rows, workflows  # return both flattened rows and full workflows


# -----------------------------
# Correlation builders
# -----------------------------

def _extract_policy_ids_from_workflow(workflow):
    """Extract numeric policy IDs from issuesFilter.predicates values when attribute includes 'policyId'."""
    ids = set()
    predicates = (workflow.get('issuesFilter') or {}).get('predicates') or []
    if isinstance(predicates, dict):
        predicates = [predicates]
    for pred in predicates:
        attr = (pred.get('attribute') or '').lower()
        if 'policyid' in attr:  # matches labels.policyIds, labels.policyId, etc.
            for v in (pred.get('values') or []):
                for tok in re.findall(r'\d+', str(v)):
                    ids.add(str(int(tok)))
    return ids


def correlate_workflows_to_policies(accounts):
    """
    Correlate Workflows -> (AI Notifications) Channels -> Policies.
    Emits one row per (workflow × destination × policy) when policy filters exist; otherwise policy cols are empty.
    """
    # Gather data
    _, workflows_full = get_all_workflows_flat_csv(accounts)
    channels = get_all_notification_channels_ai(accounts)
    policies = get_all_policies(accounts)

    # Lookups scoped by account (policy IDs are only unique within an account)
    ch_lookup = {(str(ch.get('accountId')), str(ch.get('id'))): ch for ch in channels}
    pol_lookup = {(str(p.get('accountId')), str(p.get('id'))): p.get('name') for p in policies}

    rows = []
    for wf in workflows_full:
        acct = str(wf.get('accountId'))
        dests = wf.get('destinationConfigurations') or []
        policy_ids = _extract_policy_ids_from_workflow(wf)
        if not dests:
            rows.append({
                'Account ID': acct,
                'Workflow ID': wf.get('id'),
                'Workflow Name': wf.get('name'),
                'Channel ID': None,
                'Channel Name': None,
                'Channel Type': None,
                'Policy ID': ','.join(sorted(policy_ids)) if policy_ids else None,
                'Policy Name': ','.join(pol_lookup.get((acct, pid), '') for pid in sorted(policy_ids)) if policy_ids else None,
            })
            continue
        for d in dests:
            cid = str(d.get('channelId')) if d.get('channelId') is not None else None
            ch = ch_lookup.get((acct, cid), {}) if cid else {}
            if policy_ids:
                for pid in sorted(policy_ids, key=lambda x: int(x)):
                    rows.append({
                        'Account ID': acct,
                        'Workflow ID': wf.get('id'),
                        'Workflow Name': wf.get('name'),
                        'Channel ID': cid,
                        'Channel Name': ch.get('name'),
                        'Channel Type': ch.get('type'),
                        'Policy ID': pid,
                        'Policy Name': pol_lookup.get((acct, pid)),
                    })
            else:
                rows.append({
                    'Account ID': acct,
                    'Workflow ID': wf.get('id'),
                    'Workflow Name': wf.get('name'),
                    'Channel ID': cid,
                    'Channel Name': ch.get('name'),
                    'Channel Type': ch.get('type'),
                    'Policy ID': None,
                    'Policy Name': None,
                })
    return rows


def correlate_legacy_channels_to_policies(accounts):
    """Correlate legacy Alerts notificationChannels to associatedPolicies (deprecated model)."""
    channels = get_all_notification_channels_legacy(accounts)
    rows = []
    for ch in channels:
        acct = ch.get('accountId')
        assoc = (ch.get('associatedPolicies') or {}).get('policies') or []
        if not assoc:
            rows.append({
                'Account ID': acct,
                'Channel ID': ch.get('id'),
                'Channel Name': ch.get('name'),
                'Channel Type': ch.get('type'),
                'Policy ID': None,
                'Policy Name': None,
            })
            continue
        for pol in assoc:
            rows.append({
                'Account ID': acct,
                'Channel ID': ch.get('id'),
                'Channel Name': ch.get('name'),
                'Channel Type': ch.get('type'),
                'Policy ID': pol.get('id'),
                'Policy Name': pol.get('name'),
            })
    return rows


# -----------------------------
# Policy–Condition–Workflow–Channel map
# -----------------------------

def build_policy_condition_workflow_map(
    accounts,
    policies=None,
    conditions=None,
    workflows_full=None,
    ai_channels=None
):
    """
    Build a comprehensive mapping:
    Policy (id, name, incidentPreference)
      -> Condition(s) (id, name, type)
      -> Workflow(s) that reference the Policy (via issuesFilter labels.policyIds)
          -> Destination Channel(s) used by the Workflow (AI Notifications)

    Returns a list of rows suitable for Excel export.
    """

    # Fetch if not supplied
    if policies is None:
        policies = get_all_policies(accounts)
    if conditions is None:
        conditions = get_all_alert_conditions(accounts, policies=None)
    if workflows_full is None:
        workflows_full = get_all_workflows_full(accounts)
    if ai_channels is None:
        ai_channels = get_all_notification_channels_ai(accounts)

    # Lookups
    conds_by_policy = {}
    for c in conditions:
        key = (str(c.get('accountId')), str(c.get('policyId')))
        conds_by_policy.setdefault(key, []).append(c)

    wfs_by_policy = {}
    for wf in workflows_full:
        acct = str(wf.get('accountId'))
        for pid in _extract_policy_ids_from_workflow(wf):
            wfs_by_policy.setdefault((acct, pid), []).append(wf)

    ch_by_key = {(str(ch.get('accountId')), str(ch.get('id'))): ch for ch in ai_channels}

    rows = []
    for p in policies:
        acct = str(p.get('accountId'))
        pid  = str(p.get('id'))
        pname = p.get('name')
        ipref = p.get('incidentPreference')

        conds = conds_by_policy.get((acct, pid), [None])
        wfs   = wfs_by_policy.get((acct, pid), [None])

        for c in conds:
            c_id = c.get('id') if c else None
            c_name = c.get('name') if c else None
            c_type = c.get('type') if c else None

            for wf in wfs:
                if wf is None:
                    rows.append({
                        'Account ID': acct,
                        'Policy ID': pid,
                        'Policy Name': pname,
                        'Incident Preference': ipref,
                        'Condition ID': c_id,
                        'Condition Name': c_name,
                        'Condition Type': c_type,
                        'Workflow ID': None,
                        'Workflow Name': None,
                        'Workflow Enabled': None,
                        'Channel ID': None,
                        'Channel Name': None,
                        'Channel Type': None,
                    })
                    continue

                dests = wf.get('destinationConfigurations') or [None]
                for d in dests:
                    if d is None:
                        rows.append({
                            'Account ID': acct,
                            'Policy ID': pid,
                            'Policy Name': pname,
                            'Incident Preference': ipref,
                            'Condition ID': c_id,
                            'Condition Name': c_name,
                            'Condition Type': c_type,
                            'Workflow ID': wf.get('id'),
                            'Workflow Name': wf.get('name'),
                            'Workflow Enabled': wf.get('workflowEnabled'),
                            'Channel ID': None,
                            'Channel Name': None,
                            'Channel Type': None,
                        })
                        continue

                    cid = str(d.get('channelId')) if d.get('channelId') else None
                    ch  = ch_by_key.get((acct, cid), {}) if cid else {}
                    rows.append({
                        'Account ID': acct,
                        'Policy ID': pid,
                        'Policy Name': pname,
                        'Incident Preference': ipref,
                        'Condition ID': c_id,
                        'Condition Name': c_name,
                        'Condition Type': c_type,
                        'Workflow ID': wf.get('id'),
                        'Workflow Name': wf.get('name'),
                        'Workflow Enabled': wf.get('workflowEnabled'),
                        'Channel ID': cid,
                        'Channel Name': ch.get('name'),
                        'Channel Type': ch.get('type'),
                    })
    return rows


# -----------------------------
# High-level entity collectors (CSV parity)
# -----------------------------

def get_all_apm_agents():
    output_file = f'{TIMESTAMP}-apm-agent.csv'
    results = []
    cursor = None
    while True:
        data = fetch_apm_agents(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        results.extend(entities)
        cursor = data['data']['actor']['entitySearch']['results'].get('nextCursor')
        if not cursor:
            break
    # Write CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["name","reporting","language","max_version","min_version"])
        for agent in results:
            reporting = agent.get('reporting', 'Unknown')
            language = agent.get('language', 'Unknown')
            rav = agent.get('runningAgentVersions') or {}
            w.writerow([
                agent.get('name'),
                reporting,
                language,
                rav.get('maxVersion') or 'None',
                rav.get('minVersion') or 'None',
            ])
    return results


def get_all_dashboard_data():
    output_file = f'{TIMESTAMP}-dashboards.csv'
    results = []
    cursor = None
    while True:
        data = fetch_dashboard_data(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        results.extend(entities)
        cursor = data['data']['actor']['entitySearch']['results'].get('nextCursor')
        if not cursor:
            break
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["name","accountId","entityType","lastReportingChangeAt","owner","permissions","reporting","permalink"])
        for d in results:
            try:
                w.writerow([
                    d.get('name'), d.get('accountId'), d.get('entityType'),
                    convert_epoch_to_formatted_date(d.get('lastReportingChangeAt')) if d.get('lastReportingChangeAt') else None,
                    d.get('owner'), d.get('permissions'), d.get('reporting'), d.get('permalink')
                ])
            except Exception:
                pass
    return results


def get_all_infra_agents():
    output_file = f'{TIMESTAMP}-infra-agents.csv'
    results = []
    cursor = None
    while True:
        data = fetch_infra_agents(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        results.extend(entities)
        cursor = data['data']['actor']['entitySearch']['results'].get('nextCursor')
        if not cursor:
            break
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["name","accountId","entityType","lastReportingChangeAt","reporting","permalink"])
        for e in results:
            try:
                w.writerow([
                    e.get('name'), e.get('accountId'), e.get('entityType'),
                    convert_epoch_to_formatted_date(e.get('lastReportingChangeAt')) if e.get('lastReportingChangeAt') else None,
                    e.get('reporting'), e.get('permalink')
                ])
            except Exception:
                pass
    return results


def get_all_synthetic_monitors():
    output_file = f'{TIMESTAMP}-synthetic-monitors.csv'
    results = []
    cursor = None
    while True:
        data = fetch_synthetic_monitors(cursor)
        entities = data['data']['actor']['entitySearch']['results']['entities']
        results.extend(entities)
        cursor = data['data']['actor']['entitySearch']['results'].get('nextCursor')
        if not cursor:
            break
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["name","accountId","entityType","lastReportingChangeAt","status","locationsRunning","successRate","monitorType","monitoredUrl","period","reporting"])
        for m in results:
            ms = m.get('monitorSummary') or {}
            w.writerow([
                m.get('name'), m.get('accountId'), m.get('entityType'),
                convert_epoch_to_formatted_date(m.get('lastReportingChangeAt')) if m.get('lastReportingChangeAt') else None,
                ms.get('status'), ms.get('locationsRunning'), ms.get('successRate'),
                m.get('monitorType'), m.get('monitoredUrl'), m.get('period'), m.get('reporting')
            ])
    return results


def get_all_users():
    output_file = f'{TIMESTAMP}-list-users.csv'
    results = []
    cursor = None
    while True:
        data = fetch_user_accounts(cursor)
        users = data['data']['actor']['users']['userSearch']['users']
        results.extend(users)
        cursor = data['data']['actor']['users']['userSearch'].get('nextCursor')
        if not cursor:
            break
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["email","name"])
        for u in results:
            w.writerow([u.get('email'), u.get('name')])
    return results


# -----------------------------
# Main / CLI
# -----------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Export New Relic data and build correlations.")
    parser.add_argument('--accounts', type=str, default=None,
                        help='Comma-separated list of account IDs to include (e.g. 837777,2096527). Overrides ACCOUNT_ID env.')
    parser.add_argument('--skip-apm', action='store_true', help='Skip APM agents export')
    parser.add_argument('--skip-infra', action='store_true', help='Skip Infra hosts export')
    parser.add_argument('--skip-dash', action='store_true', help='Skip Dashboards export')
    parser.add_argument('--skip-synth', action='store_true', help='Skip Synthetics export')
    parser.add_argument('--skip-users', action='store_true', help='Skip Users export')
    parser.add_argument('--no-excel', action='store_true', help='Skip Excel workbook output (still writes CSVs)')
    return parser.parse_args()


def resolve_accounts(args):
    if args.accounts:
        return [x.strip() for x in args.accounts.split(',') if x.strip()]
    if ENV_ACCOUNT_ID:
        return [ENV_ACCOUNT_ID.strip()]
    # Sensible default if nothing provided
    return ['837777', '2096527']


def main():
    require_api_key()
    args = parse_args()
    accounts = resolve_accounts(args)

    # Gather & CSV
    results_map = {}

    if not args.skip_apm:
        results_map['apm_agents'] = get_all_apm_agents()
    if not args.skip_dash:
        results_map['dashboards'] = get_all_dashboard_data()
    if not args.skip_infra:
        results_map['infras_agents'] = get_all_infra_agents()

    # Policy/Condition exports are per-accounts
    policies = get_all_policies(accounts)
    results_map['alert_policies'] = policies

    alert_conds = get_all_alert_conditions(accounts, policies=policies)
    results_map['alert_conditions'] = alert_conds

    if not args.skip_synth:
        results_map['synthetics'] = get_all_synthetic_monitors()
    if not args.skip_users:
        results_map['users'] = get_all_users()

    # Channels (AI) and Workflows
    ai_channels = get_all_notification_channels_ai(accounts)
    results_map['notifications'] = ai_channels

    workflows_flat, workflows_full = get_all_workflows_flat_csv(accounts)
    results_map['workflows'] = workflows_full  # store full for Excel; CSV already written as flattened

    # Correlations
    wf_policy_corr = correlate_workflows_to_policies(accounts)
    results_map['workflow_policy_map'] = wf_policy_corr

    legacy_corr = correlate_legacy_channels_to_policies(accounts)
    results_map['legacy_channel_policy_map'] = legacy_corr

    # Policy–Condition–Workflow–Channel map
    pcw_map = build_policy_condition_workflow_map(
        accounts,
        policies=policies,
        conditions=alert_conds,
        workflows_full=workflows_full,
        ai_channels=ai_channels
    )
    results_map['policy_condition_workflow_map'] = pcw_map

    # Excel workbook (one sheet per key)
    if not args.no_excel:
        excel_file = f'{TIMESTAMP}-nr-data-output.xlsx'
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            for sheet_name, data in results_map.items():
                try:
                    df = pd.json_normalize(data)
                except Exception:
                    df = pd.DataFrame(data)
                # Cap sheet name length for Excel
                safe_sheet = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_sheet, index=False)
        print("Excel file with multiple sheets created successfully.")

    # Summary report
    print(f"As of {TIMESTAMP[:8]} there are:")
    for k, data in results_map.items():
        try:
            print(f" {len(data):>6} {k}")
        except TypeError:
            pass


if __name__ == '__main__':
    main()