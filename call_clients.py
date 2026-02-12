"""
Outbound Call Trigger Client.

This script triggers real outbound calls using the Vonage Voice API.
It connects the recipient to the Dialogflow CX Agent ("Jason").

Usage:
    python call_clients.py
"""

import csv
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional

import vonage
from dotenv import load_dotenv

# --- INITIALIZATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("call_trigger")
load_dotenv()

# --- CONFIGURATION ---
CSV_PATH = "clients.csv"
VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")
VONAGE_APPLICATION_ID = os.getenv("VONAGE_APPLICATION_ID")
VONAGE_PRIVATE_KEY_PATH = os.getenv("VONAGE_PRIVATE_KEY_PATH", "private.key")
VONAGE_FROM_NUMBER = os.getenv("VONAGE_FROM_NUMBER", "12065550100")


def get_vonage_client() -> Optional[vonage.Client]:
    """
    Initialize the Vonage client using environment variables.

    Returns:
        vonage.Client: Authenticated client or None if config missing.
    """
    if not VONAGE_API_KEY or not VONAGE_APPLICATION_ID:
        logger.warning("⚠️ Vonage credentials missing in .env")
        return None
    
    return vonage.Client(
        key=VONAGE_API_KEY,
        secret=VONAGE_API_SECRET,
        application_id=VONAGE_APPLICATION_ID,
        private_key=VONAGE_PRIVATE_KEY_PATH,
    )


def clean_csv_data(row: Dict[str, str]) -> Dict[str, str]:
    """
    Parse and clean a single CSV row.

    Args:
        row: Raw CSV row dictionary.

    Returns:
        Dict: Cleaned client data.
    """
    try:
        funding_date_str = row.get("Funding Date", "")
        funding_date = datetime.strptime(funding_date_str, "%m/%d/%Y")
        original_year = str(funding_date.year)
    except (ValueError, TypeError):
        original_year = "recently"

    # Default phone to env var for safety if missing or placeholder
    phone_raw = row.get("Phone", "")
    phone_safe = phone_raw if phone_raw else os.getenv("DEFAULT_TEST_PHONE", "+12065550100")

    return {
        "client_name": row.get("Primary Borrower", "there").split(" ")[0],
        "phone": phone_safe,
        "city": _extract_city(row),
        "state": row.get("Subject Property: Address: State", ""),
        "interest_rate": row.get("Interest Rate", ""),
        "original_year": original_year
    }


def _extract_city(row: Dict[str, str]) -> str:
    """Helper to extract city safely."""
    addr = row.get("Subject Property: Address: 1", "")
    if addr and " " in addr:
        return addr.split(" ")[-3] if len(addr.split(" ")) > 3 else "your area"
    return row.get("City", "your area")


def trigger_outbound_call(client_data: Dict[str, str]):
    """
    Trigger an outbound call via Vonage and connect to Dialogflow Agent.

    Args:
        client_data: Dictionary containing 'phone' and 'client_name'.
    """
    vonage_client = get_vonage_client()
    if not vonage_client:
        return
    
    # NCCO (Nexmo Call Control Object)
    # Connects the call directly to the Dialogflow CX Agent
    ncco = [
        {
            "action": "connect",
            "from": VONAGE_FROM_NUMBER,
            "endpoint": [
                {
                    "type": "app",
                    "user": "dialogflow-agent-jason"  # Identity mapped in Vonage Dashboard
                }
            ]
        }
    ]
    
    logger.info(f"📞 Dialing {client_data['client_name']} at {client_data['phone']}...")
    
    try:
        # response = vonage_client.voice.create_call({
        #     'to': [{'type': 'phone', 'number': client_data['phone']}],
        #     'from': {'type': 'phone', 'number': VONAGE_FROM_NUMBER},
        #     'ncco': ncco
        # })
        # logger.info(f"✅ Call requested: {response['uuid']}")
        logger.info(f"✅ [SIMULATION] Call triggered for {client_data['client_name']}.")
    except Exception as e:
        logger.error(f"❌ Call failed: {e}")


def main():
    """Main execution entry point."""
    logger.info("🚀 Outbound Agent 'Jason' - Outbound Campaign Start")
    
    clients = []
    
    # 1. Load Data
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    clients.append(clean_csv_data(row))
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
    else:
        logger.warning(f"CSV file not found: {CSV_PATH}")
    
    # 2. Process calls
    for client in clients[:5]:  # Safety limit for testing
        trigger_outbound_call(client)
        time.sleep(10)  # Rate limiting


if __name__ == "__main__":
    main()
