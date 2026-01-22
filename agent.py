from google import genai
from google.genai import types
import os
import logging
import json
import re

logger = logging.getLogger(__name__)

class Brain:
    def __init__(self):
        self.project_id = os.environ.get("GCP_PROJECT_ID", "deployment-2026-core")
        self.location = "global" # Gemini 3 Preview models are on global endpoints
        
        try:
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
            
            # --- JASON V6: THE FULL-STACK LOAN BROKER (GEMINI 3.0 UPGRADE) ---
            self.system_prompt = """You are Jason, an expert Outbound Broker calling for Brad Overlin at Movement Mortgage. 

            GEMINI 3.0 AGENTIC PROTOCOL:
            - You have ultra-high reasoning capabilities. Use them to anticipate borrower needs.
            - Multi-channel tools: SMS, Email, Calendar, and the Movement portal.
            - If they sound busy: "Oh, [pause] I hear ya. Listen, I'll just text you the link so you have it. Does that work?"
            - Voice: Deeply natural. Use [breath], [pause], and [thinking].

            OUTBOUND CALL FLOW:
            1. OPENING: "Hey {client_name}! [pause] Jason here for Brad Overlin... did I catch you at a bad time?"
            2. THE HOOK: "Brad saw rates slide on your {original_year} loan for the place in {city}... honestly, we can probably drop that payment significantly."
            3. CALL TO ACTION: "Book a 5-min chat with Brad, or should I just text the info?"

            OUTPUT FORMAT (JSON ONLY):
            {{
                "agent_response": "The verbatim words to speak.",
                "actions": [{{"type": "send_sms|send_email|schedule|browser_automation", "body": "...", "data": {{}}}}],
                "disposition": "...",
                "extracted_data": {{"email": "...", "loan_goal": "..."}}
            }}
            """

            
            self.model_id = "gemini-3-flash-preview"
            
        except Exception as e:
            logger.error(f"Failed to init GenAI Client: {e}")
            self.client = None

    async def process_turn(self, user_text: str, context: dict = None) -> dict:
        """
        Processes a conversation turn using Gemini 3.0.
        """
        logger.info(f"User: {user_text} | Context: {context}")
        
        fallback_response = {
            "text": "<speak>Ah, I missed that side of it. Could you say it again?</speak>",
            "metadata": {}
        }
        
        if not self.client:
             return fallback_response

        ctx = context or {}
        # Simple injection for the prompt
        instruction = self.system_prompt.format(
            client_name=ctx.get("client_name", "there"),
            city=ctx.get("city", "the area"),
            original_year=ctx.get("original_year", "a while back")
        )

        try:
            # Gemini 3.0 request with MINIMAL thinking for lowest latency
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=user_text,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    response_mime_type="application/json",
                    temperature=0.7,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="MINIMAL" # High speed for telephony
                    )
                )
            )
            
            try:
                data = json.loads(response.text)
                raw_text = data.get("agent_response", "").strip()
                
                # --- SSML ENHANCEMENTS ---
                clean_text = re.sub(r'[*#\-_~\[\]\(\)]', '', raw_text)
                ssml_text = clean_text.replace("[pause]", '<break time="500ms"/>')
                ssml_text = ssml_text.replace("[breath]", '<break time="300ms"/><prosody rate="150%" pitch="-1st">Hhh.</prosody><break time="200ms"/>')
                ssml_text = ssml_text.replace("[thinking]", '<prosody pitch="-2st" rate="0.85">uhhmm...</prosody><break time="450ms"/>')
                
                final_speech = f'<speak><prosody rate="1.05" pitch="-3st">{ssml_text}</prosody></speak>'

                return {
                    "text": final_speech,
                    "metadata": {
                        "extracted_data": data.get("extracted_data", {}),
                        "disposition": data.get("disposition", "UNKNOWN")
                    },
                    "actions": data.get("actions", [])
                }
            except json.JSONDecodeError:
                return {"text": f"<speak>{response.text}</speak>", "metadata": {}}
            
        except Exception as e:
            logger.error(f"Gemini 3.0 Error: {e}")
            return fallback_response
