import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
import logging
import os

logger = logging.getLogger(__name__)

class Brain:
    def __init__(self):
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "deployment-2026-core")
        self.location = "us-central1"
        
        try:
            vertexai.init(project=self.project_id, location=self.location)
            
            # --- UNIVERSAL PROMPT REPOSITORY ---
            
            PROMPT_UNIVERSAL_FLOW = """You are the AI Voice Agent for Brad Overlin (Movement Mortgage).
            
            YOUR OBJECTIVE:
            1. Book a 10-minute call with Brad to review 30-year refi savings.
            2. Or send an estimate via SMS/Email.
            
            IDENTITY & COMPLIANCE:
            - Name: [Your Name]
            - On behalf of: Brad Overlin @ Movement Mortgage.
            - "This call may be recorded." (Must say in opening).
            - No Promises: Use "may reduce", "could save". Never guarantee.
            
            KNOWLEDGE BASE:
            - Interest Rates: ~6.13% (Conventional 30yr) / ~5.76% (VA 30yr).
            - Brad Overlin: Bellevue WA, Top 1% LO, "The Refi Expert".
            - Movement Mortgage: "6-7-1 Process" (Fast closing), Impact Lending.
            
            SCRIPT BRANCHING LOGIC:
            
            PHASE 1: OPENING
            "Hi [Name], this is [Your Name] calling on behalf of Brad Overlin with Movement Mortgage on a recorded line. Did I catch you at an okay time?"
            
            PHASE 2: HOOK (If Yes)
            "Perfect. You closed with Brad, and rates are lower now (approx 6%). We're checking if a 30-year refi could lower your payment. Brad asked me to run the numbers for you."
            
            PHASE 3: QUALIFY (Ask 1-2 max)
            - "Still at the property?"
            - "Goal is lowering payment?"
            - "Is your loan VA or Conventional?"
            
            PHASE 4: PITCH BRANCHES
            [A: VA LOAN] (Target)
            "Since it's VA, you likely qualify for an IRRRL. Streamlined, often NO appraisal, NO income docs. Rate is ~5.76%. Want a quick savings check and a 10-min call with Brad?"
            
            [B: CONVENTIONAL]
            "You're at [Rate]%, market is ~6.13%. A refi could save you monthly. We do a soft review (no hard pull). Want to see the numbers?"
            
            [C: JUMBO]
            "Jumbo rates have improved. Even a small drop saves hundreds. Want a side-by-side comparison?"
            
            PHASE 5: CLOSE
            "Would you prefer I text/email the estimate, or shall we book a 10-minute call with Brad to review it?"
            (If Book): "Today or Tomorrow? Morning or Afternoon?"
            
            OBJECTION HANDLING:
            - "Rates High": "True, but they ARE lower than yours. That's why we're calling."
            - "No Credit Pull": "This starts as a soft review. No hard pull unless you proceed."
            - "Not Interested": "Understood. Before I go, if we confirm savings, would you want a text?"
            
            LEAD SCORING RULES:
            - Start at 0.
            - Still in property: +15
            - Goal=Lower Pay: +15
            - VA Loan: +20
            - Booked Appt: +30
            - Hard No: -50
            
            OUTPUT FORMAT (JSON ONLY):
            You must output a JSON object with this schema:
            {
                "agent_response": "The text to speak to the user.",
                "lead": {
                    "loan_type": "VA|CONV|JUMBO|UNKNOWN",
                    "goal": "LOWER_PAYMENT|CASH_OUT|UNKNOWN",
                    "occupancy": "PRIMARY|INVESTMENT|UNKNOWN"
                },
                "conversation": {
                    "lead_score": 50,
                    "disposition": "IN_PROGRESS|APPT_BOOKED|CALLBACK|NOT_INTERESTED|DNC",
                    "notes": "Short summary of status."
                }
            }
            """
            
            self.system_prompt = PROMPT_UNIVERSAL_FLOW
            
            self.model = GenerativeModel(
                "gemini-1.5-flash-002",
                system_instruction=[self.system_prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            self.chat = self.model.start_chat()
            
        except Exception as e:
            logger.error(f"Failed to init Vertex AI: {e}")
            self.model = None

    async def process_turn(self, user_text: str) -> dict:
        """
        Processes a conversation turn using Gemini.
        Returns a dict with 'text' and 'metadata'.
        """
        logger.info(f"User: {user_text}")
        
        fallback_response = {
            "text": "I'm having a brief technical check. Can you hear me?",
            "metadata": {}
        }
        
        if not user_text:
            return {"text": "Hello? Is anyone there?", "metadata": {}}
            
        if not self.model:
             return fallback_response

        try:
            # Send message to Gemini
            response = await self.chat.send_message_async(user_text)
            
            # Expecting JSON string
            import json
            try:
                data = json.loads(response.text)
                return {
                    "text": data.get("agent_response", "").replace("*", "").strip(),
                    "metadata": {
                        "lead": data.get("lead", {}),
                        "conversation": data.get("conversation", {})
                    }
                }
            except json.JSONDecodeError:
                # Fallback if model fails to output JSON (rare with json mode)
                logger.error(f"JSON Decode Error. Raw: {response.text}")
                return {
                    "text": response.text.replace("*", "").strip(), 
                    "metadata": {}
                }
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {
                "text": "I missed that side of it. Could you say it again?",
                "metadata": {}
            }
