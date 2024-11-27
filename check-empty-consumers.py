import os
import subprocess
import json
import requests
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

now     = datetime.datetime.now()

def generate_timestamped_filename(base_filename, extension='csv'):
    """Generate a timestamp filename with a given base name and extension"""
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    return f"{base_filename}_{timestamp}.{extension}"

# Step 1: Run kafka-consumer-groups.sh and extract the CONSUMER-ID
def describe_consumer_group(group_name, bootstrap_servers, kafka_home, filename):
    command  = f"{kafka_home}/bin/kafka-consumer-groups.sh --bootstrap-server {bootstrap_servers} --describe --group {group_name}"
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        with open(filename, "w") as file:
            file.write(output)
        print(f"Consumer group description saved to {filename}")
    except subprocess.CalledProcessError as e:
        print(f"Error running kafka-consumer-groups.sh: {e.output}")
        return None

# Step 2: Parse consumer_group_status.txt and extract CONSUMER-ID
def extract_consumer_ids(file_path):
    consumer_ids = []
    try:
        with open(file_path, "r") as file:
            for line in file:
                if "CONSUMER-ID" in line:
                    continue  # Skip header
                parts = line.split()
                if len(parts) > 0:
                    consumer_ids.append(parts[0])  # Assuming CONSUMER-ID is the first column
        print(f"Extracted CONSUMER-ID values: {consumer_ids}")
        return consumer_ids
    except FileNotFoundError:
        print("File not found. Please ensure the file path is correct.")
        return None

# Step 3: Send CONSUMER-ID values to New Relic using their API
def send_to_new_relic(consumer_ids, api_key, account_id):
    url = f"https://insights-collector.newrelic.com/v1/accounts/{account_id}/events"
    headers = {
        "Content-Type": "application/json",
        "X-Insert-Key": api_key,
    }

    payload = [
        {
            "eventType": "KafkaConsumerID",
            "consumer_id": consumer_id,
        }
        for consumer_id in consumer_ids
    ]

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            print("Successfully sent consumer IDs to New Relic.")
        else:
            print(f"Failed to send data to New Relic: {response.status_code} {response.text}")
    except requests.RequestException as e:
        print(f"Error sending data to New Relic: {e}")

# Main function to tie everything together
def main():
    now               = datetime.datetime.now()
    kafka_home        = "/root/kafka_2.12-3.6.0"  # Replace with the path to your Kafka installation
    group_name        = "erecruit-bridge:account-management"  # Replace with your Kafka consumer group name
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVER_STG')  # Replace with your Kafka bootstrap server address
    api_key           = os.getenv('NR_API_KEY')  # Replace with your New Relic API key
    account_id        = os.getenv('NR_ACCT_ID')  # Replace with your New Relic account ID
    output_filename   = generate_timestamped_filename(f"consumer_group_{group_name}_status", "txt")
    

    # Step 1: Describe consumer group
    describe_consumer_group(group_name, bootstrap_servers, kafka_home, output_filename)

    # # Step 2: Extract CONSUMER-ID values
    # consumer_ids = extract_consumer_ids(output_filename)

    # # Step 3: Send to New Relic
    # if consumer_ids:
    #     send_to_new_relic(consumer_ids, api_key, account_id)

if __name__ == "__main__":
    main()
