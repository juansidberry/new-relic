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

TIMESTAMP  = datetime.now().strftime("%Y%m%d-%H%M%S")
OUTPUT_FILE = f"output_{TIMESTAMP}.csv"

def action_one():
    print(f"\n\tAction One selected. (Function not yet implemented)")

def action_two():
    print(f"\n\tAction Two selected. (Function not yet implemented)")

def action_three():
    print(f"\n\tAction Three selected. (Function not yet implemented)")

def delete_destination():

    # GraphQL mutation
    query = """
    mutation { aiNotificationsDeleteDestination(
        accountId: %s
        destinationId: "%s"
    ) { ids error { details }}
    }
    """ % (ACCOUNT_ID, DESTINATION_ID)


def show_menu():
    print("\nPlease choose an action:")
    print("1. Action One")
    print("2. Action Two")
    print("3. Action Three")
    print("4. delete destination")
    print("0. Exit")

def main():
    while True:
        show_menu()
        choice = input("Enter your choice: ")

        if choice == '1':
            action_one()
        elif choice == '2':
            action_two()
        elif choice == '3':
            action_three()
        elif choice == '4':
            delete_destination()
        elif choice == '0':
            print(f"\n\tExiting the program.\n")
            break
        else:
            print(f"\n\t*** Invalid choice.\n\t*** Please try again.")


if __name__ == '__main__':
    main()