"""
Test script to make a single outbound call via Vonage Voice API.
This script will call the specified number and play a text-to-speech message.
"""
import requests
import jwt
import time

# --- VONAGE CREDENTIALS ---
VONAGE_APPLICATION_ID = "dcefa55d-55cd-4f8c-a999-dc45c75950d6"
VONAGE_PRIVATE_KEY_PATH = "private.key"
VONAGE_FROM_NUMBER = "15159939004"

# --- TARGET ---
TARGET_NUMBER = "12063497715"  # User's number

def generate_jwt():
    """Generate a JWT for Vonage API authentication."""
    with open(VONAGE_PRIVATE_KEY_PATH, 'r') as f:
        private_key = f.read()
    
    payload = {
        'application_id': VONAGE_APPLICATION_ID,
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600,
        'jti': str(int(time.time()))
    }
    
    token = jwt.encode(payload, private_key, algorithm='RS256')
    return token

def make_test_call():
    """Make a test call using Vonage Voice API."""
    print("🚀 Initializing Vonage call...")
    
    token = generate_jwt()
    
    # NCCO (Nexmo Call Control Object) - defines what happens on the call
    ncco = [
        {
            "action": "talk",
            "text": "Hello! This is the Movement Voice Agent. Your AI sales assistant is now active and ready to help you close more deals.",
            "language": "en-US",
            "style": 1
        },
        {
            "action": "talk",
            "text": "Thank you for testing. Goodbye!",
            "language": "en-US"
        }
    ]
    
    payload = {
        "to": [{"type": "phone", "number": TARGET_NUMBER}],
        "from": {"type": "phone", "number": VONAGE_FROM_NUMBER},
        "ncco": ncco
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"📞 Calling {TARGET_NUMBER} from {VONAGE_FROM_NUMBER}...")
    
    try:
        response = requests.post(
            "https://api.nexmo.com/v1/calls",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Call initiated! UUID: {data.get('uuid')}")
            print(f"   Status: {data.get('status')}")
            return data
        else:
            print(f"❌ Call failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Call failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    make_test_call()

