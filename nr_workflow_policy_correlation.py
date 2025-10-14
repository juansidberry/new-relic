import pandas as pd
from newrelic_data_exporter import get_all_workflows, get_all_notification_channels, get_all_policies
from datetime import datetime

def correlate_workflows_to_policies():
    workflows = get_all_workflows()
    channels = get_all_notification_channels()
    policies = get_all_policies()
    channel_lookup = {str(channel['id']): channel for channel in channels}
    policy_lookup = {str(policy['id']): policy['name'] for policy in policies}
    correlation_results = []
    for wf in workflows:
        for dest in wf.get('destinationConfigurations', []):
            channel_id = str(dest.get('channelId'))
            if channel_id and channel_id in channel_lookup:
                channel = channel_lookup[channel_id]
                associated_policies = channel.get('associatedPolicies', {}).get('policies', [])
                for policy in associated_policies:
                    correlation_results.append({
                        'Workflow Name': wf.get('name'),
                        'Channel Name': channel.get('name'),
                        'Channel Type': channel.get('type'),
                        'Policy Name': policy.get('name'),
                        'Policy ID': policy.get('id')
                    })
    return correlation_results

if __name__ == "__main__":
    TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
    results = correlate_workflows_to_policies()
    if results:
        df = pd.DataFrame(results)
        csv_file = f'{TIMESTAMP}-workflow-policy-correlation.csv'
        df.to_csv(csv_file, index=False)
        print(f"Standalone CSV file created: {csv_file}")
    else:
        print("No correlations found.")