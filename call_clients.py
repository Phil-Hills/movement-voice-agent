import csv
import json
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
CSV_PATH = "clients.csv"
GCP_PROJECT = "deployment-2026-core"
AGENT_PHONE_NUMBER = "+16196306631" # Current Dialogflow Agent Number
# TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
# TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")

def clean_csv_data(row):
    """Parses and cleans a single CSV row."""
    try:
        funding_date = datetime.strptime(row.get("Funding Date", ""), "%m/%d/%Y")
        original_year = funding_date.year
        original_month = funding_date.strftime("%B")
    except:
        original_year = "recently"
        original_month = ""

    return {
        "client_name": row.get("Primary Borrower", "there").split(" ")[0],
        "phone": "+1" + row.get("Loan Number", ""), # Placeholder: Need actual phone column
        "city": row.get("Subject Property: Address: 1", "").split(" ")[-3], # Guessing city from address
        "state": row.get("Subject Property: Address: State", ""),
        "interest_rate": row.get("Interest Rate", ""),
        "original_year": original_year,
        "original_month": original_month
    }

def process_outbound_list():
    print(f"🚀 Initializing Outbound Sequence using {CSV_PATH}...")
    
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            client = clean_csv_data(row)
            
            print(f"--- Preparing call for {client['client_name']} ---")
            print(f"📍 Location: {client['city']}, {client['state']}")
            print(f"💰 Current Rate: {client['interest_rate']} (Closed {client['original_year']})")
            
            # --- OUTBOUND TRIGGER LOGIC ---
            # 1. Dial client
            # 2. On answer, connect to AGENT_PHONE_NUMBER
            # 3. Pass client data as SIP headers or custom parameters
            
            print(f"SIMULATION: Dialing {client['phone']}... Connecting to Jason.")
            
            # Example Twilio Trigger (Requires package: twilio)
            # if TWILIO_ACCOUNT_SID:
            #     from twilio.rest import Client
            #     client_tw = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            #     call = client_tw.calls.create(
            #         to="+12063497715", # Using your number for testing
            #         from_=TWILIO_FROM_NUMBER,
            #         url=f"http://twimlets.com/forward?PhoneNumber={AGENT_PHONE_NUMBER}"
            #     )
            
            # Wait between calls to avoid spamming
            time.sleep(2)

if __name__ == "__main__":
    process_outbound_list()
