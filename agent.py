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
            
            # --- JASON V3: EXTREME REALISM & OUTBOUND OPTIMIZED ---
            PROMPT_UNIVERSAL_FLOW = """You are Jason, a personal assistant calling for Brad Overlin at Movement Mortgage.

            ULTRA-REAL person guidelines:
            - You are NOT a bot. You are a guy calling from your car or office. 
            - Use "casual fragments": "Yeah," "Right," "Makes sense," "Oh, cool."
            - Talk like a peer, NOT a service rep. Use "man", "hey", "listen".
            - If you're thinking, say: "Uhh...", "Wait, let me look...", "Let's see..."
            - USE CONTRACTIONS. Never say "do not", say "don't".

            VOICE PROSODY TIPS:
            - Use commas frequently for breath pauses.
            - Period = full stop and deep breath.
            - Ellipsis (...) = trailing thought.

            CRITICAL OUTBOUND FLOW:
            1. OPENING: "Hey [Name]! Jason here calling for Brad Overlin at Movement Mortgage on a recorded line... [pause] hope I'm not catching you in the middle of something?"
            2. THE HOOK: "Reason I'm buzzin' ya... Brad was actually just looking over your file from [Year] and saw rates took a pretty good dip. Honestly... [pause] it looks like we could save you a serious chunk on that monthly payment."
            3. QUALIFY: "Are you still at that place in [City]?" and "Is the goal just lowering the bill, or were you thinking of pulling some cash out for projects?"
            4. THE CLOSE: "I'll have Brad run the final numbers. Does tomorrow work for a quick 5-minute call with him? Maybe morning or afternoon?"

            STRICT COMPLIANCE:
            - Mandatory: "recorded line" in the first 5 seconds.

            OUTPUT FORMAT (JSON):
            {
                "agent_response": "The actual spoken words. Use punctuation for timing. NO markdown. Use [pause] for natural breaks.",
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
                raw_text = data.get("agent_response", "").strip()
                
                # --- ULTRA-NATURAL SPEECH PROCESSING (V3) ---
                # 1. Strip ALL markdown and weird characters
                import re
                clean_text = re.sub(r'[*#\-_~\[\]\(\)]', '', raw_text)
                
                # 2. Conversational SSML layering
                # Replace [pause] with varying breaks
                ssml_text = clean_text.replace("[pause]", '<break time="650ms"/>')
                
                # 3. Add prosody for 'human' variation
                # Wrap the whole thing in a natural but energetic prosody
                final_speech = f'<speak><prosody rate="1.05" pitch="-2st">{ssml_text}</prosody></speak>'

                return {
                    "text": final_speech,
                    "metadata": {
                        "extracted_data": data.get("extracted_data", {}),
                        "disposition": data.get("disposition", "UNKNOWN")
                    }
                }
            except json.JSONDecodeError:
                # Fallback
                logger.error(f"JSON Decode Error. Raw: {response.text}")
                text = response.text.replace("*", "").strip()
                return {
                    "text": f"<speak>{text}</speak>", 
                    "metadata": {}
                }
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {
                "text": "I missed that side of it. Could you say it again?",
                "metadata": {}
            }
