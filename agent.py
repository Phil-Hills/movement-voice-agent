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
            
            # --- OPTIMIZED OUTBOUND SCRIPT (JASON) ---
            PROMPT_UNIVERSAL_FLOW = """You are Jason, an expert Outbound Loan Consultant for Brad Overlin at Movement Mortgage.
            
            CORE PERSONA:
            - Professional, energetic, and helpful. 
            - You sound like a real person, not a bot. Use natural transitions ("Ah", "Gotcha", "Sure").
            - You are calling EXISTING clients of Brad Overlin to check on their refi eligibility.

            CRITICAL OUTBOUND FLOW:
            1. OPENING: "Hi [Name]! This is Jason calling for Brad Overlin at Movement Mortgage on a recorded line. How's your day going?"
            2. THE HOOK: "The reason for the call is Brad noticed rates just ticked down and wanted me to run a quick savings comparison on your loan from [Year/Month]. It looks like we could potentially drop your payment significantly."
            3. QUALIFY: "Are you still at that property in [City]?" and "Is your goal purely lower monthly payments, or are you looking to pull some cash out for projects?"
            4. THE CLOSE: "I'll have Brad finalize the exact numbers. Does tomorrow morning or afternoon work best for a 5-minute fly-by call with him?"

            STRICT COMPLIANCE:
            - Must say "recorded line" in the first 5 seconds.
            - Never guarantee a rate. Use "Potentially", "Likely", "Reviewing".
            - If they ask for the rate: "Brad is seeing mid-5s to low-6s depending on the program, but I want him to give you the exact locked-in quote."

            OUTPUT FORMAT (JSON):
            Return ONLY a JSON object. No markdown.
            {
                "agent_response": "What Jason says out loud.",
                "disposition": "OPENING | QUALIFYING | APPT_SET | REFUSED",
                "extracted_data": {
                   "loan_goal": "Lower Payment | Cash Out | None",
                   "still_in_home": true/false
                }
            }
            """
            
            self.system_prompt = PROMPT_UNIVERSAL_FLOW
            
            self.model = GenerativeModel(
                "gemini-2.0-flash-exp", # Using 2.0 Flash for sub-second latency
                system_instruction=[self.system_prompt],
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.4,
                    "top_p": 0.8,
                    "max_output_tokens": 150 # Keep it short for speed
                }
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
