
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add current dir to sys.path
sys.path.append(os.getcwd())

from salesforce_client import SalesforceClient

print("--- Verifying Salesforce Connection ---")
print(f"Username: {os.getenv('SF_USERNAME')}")
print(f"Instance: {os.getenv('SF_INSTANCE_URL')}")

try:
    client = SalesforceClient()
    if client.is_connected:
        print("\n✅ VERIFICATION SUCCESSFUL: Connected to Salesforce.")
        
        # Try a simple query to be sure
        print("\nTesting Query (User info)...")
        try:
            res = client.sf.query("SELECT Id, Name, Email FROM User WHERE Username = '" + os.getenv('SF_USERNAME') + "'")
            if res['totalSize'] > 0:
                 user = res['records'][0]
                 print(f"Found User: {user['Name']} ({user['Email']})")
            else:
                 print("Query successful but user not found (might be permissions).")
        except Exception as qe:
            print(f"Query failed: {qe}")

    else:
        print("\n❌ VERIFICATION FAILED: Could not connect.")
except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
