"""
Campaign Manager - Outbound Dialer Orchestrator.

This module handles the lifecycle of outbound calling campaigns.
It supports loading leads from CSV or Salesforce and executing
a power-dialing sequence.

MODE: SIMULATION / DEMO
This module currently runs in a simulated environment for demonstration
and hackathon purposes. It generates realistic call outcomes and
updates the dashboard without triggering actual telephony charges.
"""

import asyncio
import csv
import io
import logging
import random
from typing import Any, Dict, List, Optional

from salesforce_client import get_salesforce_client

logger = logging.getLogger(__name__)


class CampaignManager:
    """
    Manages outbound calling campaigns in Simulation Mode.

    Handles CSV parsing, queuing, and dialer simulation.
    Interacts with SalesforceClient to log activity.
    """
    
    def __init__(self):
        """Initialize the campaign manager with a connection to Salesforce (or mock)."""
        self.sf_client = get_salesforce_client()
        self.active_campaign: List[Dict[str, Any]] = []
        self.is_running = False
        self.current_lead_index = 0
        self.stats = {
            "total": 0,
            "dialed": 0,
            "connected": 0,
            "appointments": 0
        }

    async def load_campaign_from_csv(self, file_content: bytes) -> Dict[str, Any]:
        """
        Parse CSV content and load into active campaign.

        Args:
            file_content: Raw bytes from the uploaded CSV file.

        Returns:
            Dict containing success status and count.
        """
        try:
            self.active_campaign = []
            self.current_lead_index = 0
            
            # Decode and parse
            content_str = file_content.decode('utf-8')
            f = io.StringIO(content_str)
            reader = csv.DictReader(f)
            
            for row in reader:
                # Normalize data structure with safe defaults
                lead = {
                    "name": row.get("Primary Borrower") or row.get("Name", "Unknown"),
                    "email": row.get("Primary Borrower: Email") or row.get("Email", ""),
                    "phone": row.get("Phone") or row.get("Mobile", ""),
                    "city": self._extract_city(row),
                    "state": row.get("Subject Property: Address: State") or row.get("State", "WA"),
                    "loan_amount": row.get("Total Loan Amount") or row.get("Amount", "$0"),
                    "interest_rate": row.get("Interest Rate", "0.0%"),
                    "company": "Movement Mortgage"
                }
                self.active_campaign.append(lead)
            
            self._reset_stats(len(self.active_campaign))
            return {"success": True, "count": len(self.active_campaign)}
            
        except Exception as e:
            logger.error(f"Failed to load campaign: {e}")
            return {"success": False, "error": str(e)}

    async def load_campaign_from_salesforce(self, campaign_id: str) -> Dict[str, Any]:
        """
        Load leads directly from a Salesforce Campaign.

        Args:
            campaign_id: The Salesforce Campaign ID.

        Returns:
            Dict containing success status and count.
        """
        try:
            self.active_campaign = []
            self.current_lead_index = 0
            
            # Fetch from Salesforce
            sf_leads = self.sf_client.get_leads_for_campaign(campaign_id)
            
            for row in sf_leads:
                lead = {
                    "name": f"{row.get('FirstName', '')} {row.get('LastName', '')}".strip(),
                    "email": row.get('Email', ''),
                    "phone": row.get('Phone', ''),
                    "city": row.get('City', 'Unknown'),
                    "state": row.get('State', 'WA'),
                    "company": row.get('Company', 'Movement Mortgage'),
                    "sf_id": row.get('Id')
                }
                self.active_campaign.append(lead)
            
            self._reset_stats(len(self.active_campaign))
            return {"success": True, "count": len(self.active_campaign)}
            
        except Exception as e:
            logger.error(f"Failed to load Salesforce campaign: {e}")
            return {"success": False, "error": str(e)}

    async def start_campaign(self):
        """Start the async dialing process."""
        if self.is_running:
            return
        
        self.is_running = True
        asyncio.create_task(self._run_dialer())

    async def stop_campaign(self):
        """Stop the dialing process."""
        self.is_running = False

    async def _run_dialer(self):
        """
        Background loop to process leads.

        This method simulates the behavior of a power dialer:
        1. Dials the number (simulated delay).
        2. Determines an outcome (weighted random).
        3. Logs the result to the dashboard/Salesforce.
        """
        logger.info("🚀 Starting Campaign Dialer (SIMULATION MODE)...")
        
        while self.is_running and self.current_lead_index < len(self.active_campaign):
            lead = self.active_campaign[self.current_lead_index]
            self.current_lead_index += 1
            
            # 1. Update Stats - Dialing
            self.stats["dialed"] += 1
            logger.info(f"📞 Dialing {lead['name']}...")
            
            # Simulate "Dialing" state in Dashboard
            if not self.sf_client.is_connected:
                self.sf_client.log_demo_activity(
                    lead_name=lead['name'],
                    status="Dialing...",
                    company=lead['company'],
                    notes=f"Initiating outbound call to {lead['state']}..."
                )
            
            # Simulate Ringing Duration
            await asyncio.sleep(random.uniform(2, 4))
            
            # 2. Simulate Outcome
            outcome_data = self._simulate_outcome()
            outcome, notes = outcome_data["outcome"], outcome_data["notes"]
            
            # Simulate Conversation Duration if connected
            if "Connected" in outcome or "APPOINTMENT" in outcome:
                await asyncio.sleep(random.uniform(3, 6))
            
            # 3. Log Result
            status = self._update_stats_for_outcome(outcome)
            
            # Update Dashboard
            recording_link = f"/api/recordings/demo_{lead.get('name', 'user').replace(' ', '_')}.mp3"
            
            # Log to activity stream
            self.sf_client.log_demo_activity(
                lead_name=lead['name'],
                status=status,
                company=lead['company'],
                notes=notes,
                recording_url=recording_link
            )
            
            # Pause before next call
            await asyncio.sleep(random.uniform(2, 5))
        
        self.is_running = False
        logger.info("🏁 Campaign Completed.")

    def _extract_city(self, row: Dict[str, str]) -> str:
        """Helper to safely extract city from messy CSV data."""
        addr = row.get("Subject Property: Address: 1", "")
        if " " in addr:
             # Heuristic: assume city is near the end or fallback
             return addr.split(" ")[-3] if len(addr.split(" ")) > 3 else "Unknown"
        return row.get("City", "Unknown")

    def _reset_stats(self, total: int):
        """Reset campaign statistics."""
        self.stats = {
            "total": total,
            "dialed": 0,
            "connected": 0,
            "appointments": 0
        }

    def _simulate_outcome(self) -> Dict[str, str]:
        """
        Generate a weighted random call outcome.

        Returns:
            Dict with 'outcome' and 'notes'.
        """
        outcomes = [
            ("Voicemail", "Left voicemail about refinance rates."),
            ("Connected - Not Interested", "Client happy with current rate."),
            ("Connected - Callback", "Requested callback next Tuesday."),
            ("APPOINTMENT BOOKED", "Scheduled consultation for refinance!")
        ]

        # Weighted probabilities: 40% VM, 30% No, 20% Callback, 10% Appt
        choice = random.choices(outcomes, weights=[40, 30, 20, 10], k=1)[0]
        return {"outcome": choice[0], "notes": choice[1]}

    def _update_stats_for_outcome(self, outcome: str) -> str:
        """
        Update internal stats based on outcome and return status string.

        Args:
            outcome: The outcome string from simulation.

        Returns:
            The display status string.
        """
        if "APPOINTMENT" in outcome:
            self.stats["appointments"] += 1
            self.stats["connected"] += 1
            return "Qualified - Appointment"
        elif "Connected" in outcome:
            self.stats["connected"] += 1
            return "Working - Contacted"

        return "Open - Not Contacted"


# Singleton instance
_manager = None

def get_campaign_manager() -> CampaignManager:
    """
    Get the singleton CampaignManager instance.

    Returns:
        CampaignManager: The active instance.
    """
    global _manager
    if _manager is None:
        _manager = CampaignManager()
    return _manager
