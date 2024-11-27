import os
import subprocess
import json
import requests

# Step 1: Run kafka-consumer-groups.sh and extract the CONSUMER-ID
def describe_consumer_group(group_name, bootstrap_servers, kafka_home):
    command = f"{kafka_home}/bin/kafka-consumer-groups.sh --bootstrap-server {bootstrap_servers} --describe --group {group_name}"
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        with open("consumer_group_status.txt", "w") as file:
            file.write(output)
        print("Consumer group description saved to consumer_group_status.txt")
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
    kafka_home        = "/root/kafka_2.12-3.6.0"  # Replace with the path to your Kafka installation
    group_name        = "your_consumer_group"  # Replace with your Kafka consumer group name
    bootstrap_servers = "localhost:9092"  # Replace with your Kafka bootstrap server address
    api_key           = "your_new_relic_api_key"  # Replace with your New Relic API key
    account_id        = "your_new_relic_account_id"  # Replace with your New Relic account ID

    # Step 1: Describe consumer group
    describe_consumer_group(group_name, bootstrap_servers, kafka_home)

    # Step 2: Extract CONSUMER-ID values
    consumer_ids = extract_consumer_ids("consumer_group_status.txt")

    # Step 3: Send to New Relic
    if consumer_ids:
        send_to_new_relic(consumer_ids, api_key, account_id)

if __name__ == "__main__":
    main()
