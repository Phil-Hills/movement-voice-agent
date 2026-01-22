"""
Salesforce AgentForce Integration Client

This module provides integration with Salesforce CRM for the Movement Voice Agent.
It handles authentication, lead retrieval, disposition updates, and task creation.

Part of the Q Protocol dual-orchestrator architecture.
"""

from simple_salesforce import Salesforce
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class SalesforceClient:
    """
    Salesforce CRM client for Movement Voice Agent.
    
    Implements the Salesforce-side orchestrator of the Q Protocol,
    syncing agent state, lead data, and call dispositions.
    """
    
    def __init__(self):
        """Initialize Salesforce connection using environment variables."""
        self.sf: Optional[Salesforce] = None
        self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to Salesforce."""
        try:
            username = os.environ.get("SF_USERNAME")
            password = os.environ.get("SF_PASSWORD")
            security_token = os.environ.get("SF_TOKEN")
            domain = os.environ.get("SF_DOMAIN", "login")  # 'login' for prod, 'test' for sandbox
            
            if not all([username, password, security_token]):
                logger.warning("Salesforce credentials not configured. Running in demo mode.")
                return False
            
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain
            )
            logger.info("✅ Connected to Salesforce successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Salesforce connection failed: {e}")
            self.sf = None
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if Salesforce connection is active."""
        return self.sf is not None
    
    # =========================================================================
    # LEAD OPERATIONS
    # =========================================================================
    
    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a lead by ID.
        
        Args:
            lead_id: Salesforce Lead ID (18 characters)
            
        Returns:
            Lead record dict or None
        """
        if not self.is_connected:
            return self._demo_lead(lead_id)
        
        try:
            lead = self.sf.Lead.get(lead_id)
            return dict(lead)
        except Exception as e:
            logger.error(f"Failed to get lead {lead_id}: {e}")
            return None
    
    def get_leads_for_campaign(self, campaign_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get leads associated with a campaign.
        
        Args:
            campaign_id: Salesforce Campaign ID
            limit: Maximum number of leads to return
            
        Returns:
            List of lead records
        """
        if not self.is_connected:
            return [self._demo_lead(f"demo_{i}") for i in range(3)]
        
        try:
            query = f"""
                SELECT Id, FirstName, LastName, Phone, Email, 
                       Company, Status, LeadSource, 
                       City, State, Description
                FROM Lead 
                WHERE Campaign__c = '{campaign_id}'
                AND Status != 'Converted'
                LIMIT {limit}
            """
            result = self.sf.query(query)
            return result.get('records', [])
        except Exception as e:
            logger.error(f"Failed to query leads for campaign {campaign_id}: {e}")
            return []
    
    def update_lead_disposition(
        self, 
        lead_id: str, 
        disposition: str,
        notes: Optional[str] = None,
        call_count: Optional[int] = None
    ) -> bool:
        """
        Update lead with call disposition.
        
        Args:
            lead_id: Salesforce Lead ID
            disposition: Call outcome (e.g., "Callback Scheduled", "Not Interested")
            notes: Optional call notes
            call_count: Current call attempt number (1-11 for full cadence)
            
        Returns:
            Success status
        """
        if not self.is_connected:
            logger.info(f"[DEMO] Would update lead {lead_id} with disposition: {disposition}")
            return True
        
        try:
            update_data = {
                "Status": self._map_disposition_to_status(disposition),
                "Description": notes or f"AI Agent call - {disposition}"
            }
            
            # Custom fields for call tracking (if they exist in org)
            if call_count:
                update_data["Call_Attempt__c"] = call_count
            
            self.sf.Lead.update(lead_id, update_data)
            logger.info(f"✅ Updated lead {lead_id}: {disposition}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update lead {lead_id}: {e}")
            return False
    
    def _map_disposition_to_status(self, disposition: str) -> str:
        """Map agent disposition to Salesforce Lead Status."""
        mapping = {
            "INTERESTED": "Working - Contacted",
            "CALLBACK_SCHEDULED": "Working - Contacted",
            "NOT_INTERESTED": "Closed - Not Converted",
            "VOICEMAIL": "Open - Not Contacted",
            "NO_ANSWER": "Open - Not Contacted",
            "WRONG_NUMBER": "Closed - Not Converted",
            "DO_NOT_CALL": "Closed - Not Converted",
            "APPOINTMENT_BOOKED": "Qualified"
        }
        return mapping.get(disposition, "Open - Not Contacted")
    
    # =========================================================================
    # TASK OPERATIONS (for 11-touch cadence tracking)
    # =========================================================================
    
    def create_task(
        self,
        lead_id: str,
        subject: str,
        description: str,
        due_date: Optional[datetime] = None,
        priority: str = "Normal"
    ) -> Optional[str]:
        """
        Create a follow-up task for a lead.
        
        Args:
            lead_id: Related Lead ID
            subject: Task subject
            description: Task description/notes
            due_date: When the task is due
            priority: High, Normal, or Low
            
        Returns:
            Created Task ID or None
        """
        if not self.is_connected:
            logger.info(f"[DEMO] Would create task for lead {lead_id}: {subject}")
            return "demo_task_id"
        
        try:
            task_data = {
                "WhoId": lead_id,
                "Subject": subject,
                "Description": description,
                "Priority": priority,
                "Status": "Not Started",
                "Type": "Call",
                "ActivityDate": due_date.strftime("%Y-%m-%d") if due_date else None
            }
            
            result = self.sf.Task.create(task_data)
            task_id = result.get('id')
            logger.info(f"✅ Created task {task_id} for lead {lead_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task for lead {lead_id}: {e}")
            return None
    
    def log_call(
        self,
        lead_id: str,
        call_outcome: str,
        duration_seconds: int,
        notes: str,
        call_number: int = 1
    ) -> Optional[str]:
        """
        Log a completed call as a Task.
        
        This is part of the 11-touch cadence - each call is logged
        and the next follow-up is scheduled automatically.
        
        Args:
            lead_id: Related Lead ID
            call_outcome: Disposition of the call
            duration_seconds: Call duration
            notes: Conversation summary
            call_number: Which call in the cadence (1-11)
            
        Returns:
            Created Task ID or None
        """
        subject = f"AI Agent Call #{call_number} - {call_outcome}"
        description = f"""
Call Duration: {duration_seconds // 60}m {duration_seconds % 60}s
Outcome: {call_outcome}
Call Number: {call_number} of 11

Notes:
{notes}
        """.strip()
        
        return self.create_task(
            lead_id=lead_id,
            subject=subject,
            description=description,
            priority="Normal"
        )
    
    # =========================================================================
    # CONTACT OPERATIONS
    # =========================================================================
    
    def get_contact_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Look up a contact by phone number.
        
        Args:
            phone: Phone number to search
            
        Returns:
            Contact record or None
        """
        if not self.is_connected:
            return self._demo_contact(phone)
        
        try:
            # Normalize phone format
            clean_phone = ''.join(filter(str.isdigit, phone))
            
            query = f"""
                SELECT Id, FirstName, LastName, Phone, Email, AccountId
                FROM Contact
                WHERE Phone LIKE '%{clean_phone[-10:]}%'
                LIMIT 1
            """
            result = self.sf.query(query)
            records = result.get('records', [])
            return records[0] if records else None
            
        except Exception as e:
            logger.error(f"Failed to lookup contact by phone {phone}: {e}")
            return None
    
    # =========================================================================
    # DEMO/TESTING HELPERS
    # =========================================================================
    
    def _demo_lead(self, lead_id: str) -> Dict[str, Any]:
        """Return demo lead data when not connected to Salesforce."""
        return {
            "Id": lead_id,
            "FirstName": "Demo",
            "LastName": "User",
            "Phone": "+1-555-123-4567",
            "Email": "demo@example.com",
            "Company": "Demo Company",
            "Status": "Open - Not Contacted",
            "City": "Seattle",
            "State": "WA",
            "Description": "Demo lead for testing"
        }
    
    def _demo_contact(self, phone: str) -> Dict[str, Any]:
        """Return demo contact data when not connected to Salesforce."""
        return {
            "Id": "demo_contact",
            "FirstName": "Demo",
            "LastName": "Contact",
            "Phone": phone,
            "Email": "demo@example.com",
            "AccountId": "demo_account"
        }


# Singleton instance for easy import
_client: Optional[SalesforceClient] = None


def get_salesforce_client() -> SalesforceClient:
    """Get the singleton Salesforce client instance."""
    global _client
    if _client is None:
        _client = SalesforceClient()
    return _client
