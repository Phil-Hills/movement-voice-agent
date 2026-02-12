import csv
import json
import os
import time
from datetime import datetime
import vonage
from dotenv import load_dotenv

# --- INITIALIZATION ---
load_dotenv()

# --- CONFIGURATION ---
CSV_PATH = "clients.csv"
VONAGE_API_KEY = os.environ.get("VONAGE_API_KEY")
VONAGE_API_SECRET = os.environ.get("VONAGE_API_SECRET")
VONAGE_APPLICATION_ID = os.environ.get("VONAGE_APPLICATION_ID")
VONAGE_PRIVATE_KEY_PATH = "private.key"
VONAGE_FROM_NUMBER = os.environ.get("VONAGE_FROM_NUMBER") # Your Vonage number

# --- SALESFORCE CONFIG (Optional) ---
SF_USERNAME = os.environ.get("SF_USERNAME")
SF_PASSWORD = os.environ.get("SF_PASSWORD")
SF_TOKEN = os.environ.get("SF_TOKEN")

def get_vonage_client():
    """Initializes the Vonage client."""
    if not VONAGE_API_KEY or not VONAGE_APPLICATION_ID:
        print("⚠️ Vonage credentials missing in .env")
        return None
    
    return vonage.Client(
        key=VONAGE_API_KEY,
        secret=VONAGE_API_SECRET,
        application_id=VONAGE_APPLICATION_ID,
        private_key=VONAGE_PRIVATE_KEY_PATH,
    )

def clean_csv_data(row):
    """Parses and cleans a single CSV row."""
    try:
        funding_date_str = row.get("Funding Date", "")
        funding_date = datetime.strptime(funding_date_str, "%m/%d/%Y")
        original_year = funding_date.year
    except:
        original_year = "recently"

    return {
        "client_name": row.get("Primary Borrower", "there").split(" ")[0],
        # Note: In the example CSV, 'Loan Number' was used as phone placeholder. 
        # User needs to ensure a 'Phone' column exists.
        "phone": row.get("Phone", "+12063497715"), # Defaulting to User's number for safety
        "city": row.get("Subject Property: Address: 1", "your area").split(" ")[-3] if " " in row.get("Subject Property: Address: 1", "") else "your area",
        "state": row.get("Subject Property: Address: State", ""),
        "interest_rate": row.get("Interest Rate", ""),
        "original_year": original_year
    }

def trigger_outbound_call(client_data):
    """Triggers an outbound call via Vonage and connects to Dialogflow Agent."""
    vonage_client = get_vonage_client()
    if not vonage_client:
        return
    
    # NCCO (Nexmo Call Control Object)
    # This NCCO connects the call directly to the Dialogflow CX Agent
    ncco = [
        {
            "action": "connect",
            "from": VONAGE_FROM_NUMBER,
            "endpoint": [
                {
                    "type": "app",
                    "user": "dialogflow-agent-jason" # Identity mapped in Vonage Dashboard
                }
            ]
        }
    ]
    
    # Note: The mapping between Vonage and Dialogflow is usually done via the
    # Vonage Dashboard / Dialogflow Connector. 
    # For a direct API trigger, the NCCO can also specify the dialogflow action:
    # {
    #   "action": "talk", "text": "Connecting you to Jason..."
    # },
    # {
    #   "action": "connect", 
    #   "endpoint": [{"type": "websocket", "uri": "...", "content-type": "audio/l16;rate=16000"}]
    # }
    
    print(f"📞 Dialing {client_data['client_name']} at {client_data['phone']}...")
    
    try:
        # response = vonage_client.voice.create_call({
        #     'to': [{'type': 'phone', 'number': client_data['phone']}],
        #     'from': {'type': 'phone', 'number': VONAGE_FROM_NUMBER},
        #     'ncco': ncco
        # })
        # print(f"✅ Call requested: {response['uuid']}")
        print(f"✅ [SIMULATION] Call triggered for {client_data['client_name']}.")
    except Exception as e:
        print(f"❌ Call failed: {e}")

def process_salesforce_leads():
    """Example function to pull leads from Salesforce."""
    if not SF_USERNAME:
        return []
    
    print("☁️ Pulling leads from Salesforce...")
    # from simple_salesforce import Salesforce
    # sf = Salesforce(username=SF_USERNAME, password=SF_PASSWORD, security_token=SF_TOKEN)
    # results = sf.query("SELECT Name, Phone, City, Interest_Rate__c FROM Lead WHERE Status = 'New'")
    return []

def main():
    print(f"🚀 Outbound Agent 'Jason' - Outbound Campaign Start")
    
    # 1. Choose data source
    clients = []
    
    # Try CSV
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                clients.append(clean_csv_data(row))
    
    # 2. Process calls
    for client in clients[:5]: # Start with first 5 for testing
        trigger_outbound_call(client)
        time.sleep(10) # GAP between calls

if __name__ == "__main__":
    main()
