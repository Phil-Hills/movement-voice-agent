import logging
from core.agent_engine import AgentEngine
from agent_interface import BaseAgent
import os

logger = logging.getLogger("movement_agent")

class MovementAgent(BaseAgent):
    """
    The specific 'Jason' agent for Movement Mortgage.
    Implements the Q Protocol and A2AC interface.
    """
    
    def __init__(self):
        super().__init__(
            name="Jason",
            description="Movement Mortgage Specialist - Friendly, Professional, Compliant",
            capabilities=["mortgage", "salesforce", "telephony", "research"]
        )
        self.engine = AgentEngine(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT", "deployment-2026-core")
        )

    async def generate_response(self, user_input: str, lead_context: dict = None) -> str:
        """Generates a response using the unified Jason persona."""
        response = await self.engine.get_response(user_input, lead_context)
        return response.get("text", "I'm sorry, I'm having trouble processing that right now.")

    def record_disposition(self, lead_id: str, disposition: str):
        """Records the call disposition in the audit log."""
        receipt = self.create_ad_hoc_receipt(
            action="CALL_DISPOSITION",
            details=f"Lead: {lead_id} Disposition: {disposition}",
            status="success"
        )
        logger.info(f"✍️ AGENT RECEIPT: {receipt.to_receipt()}")
        return receipt
