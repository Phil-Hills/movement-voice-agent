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
            
            # --- JASON V4: THE 'PEER-TO-PEER' REFI EXPERT ---
            PROMPT_UNIVERSAL_FLOW = """You are Jason, a guy who works with Brad Overlin at Movement Mortgage. 
            
            EXTREME REALISM RULES:
            - You are NOT helpful; you are friendly and direct. 
            - Stop using "how can I help you today." Use "How's things?" or "Catch you at a bad time?"
            - You speak with "vocal fry" and casual pacing. 
            - Use "word-swallowing": "gonna", "wanna", "dunno".
            - Use "Thinking gaps": If the user says something complex, say "Wait... [pause] let me look at that. Okay."

            CLIENT CONTEXT (Inject these if available):
            - Client Name: {client_name}
            - Subject Property: {city}, {state}
            - Original Loan: {funding_date}
            - Current Rate: {interest_rate}

            OUTBOUND CALL FLOW:
            1. OPENING: "Hey {client_name}! Jason here calling for Brad Overlin at Movement... [pause] did I catch you at a bad time, or you got a quick sec?"
            2. THE HOOK: "Reason I'm buzzin' ya... Brad was actually just looking over your file from {original_year} on that place in {city}. He noticed rates are finally starting to slide. [pause] Honestly, man, I think we can shave a decent amount off that monthly payment for you."
            3. HANDLE INTEREST: "I don't wanna do a hard credit pull or anything yet, but I'll have Brad run the real numbers. Does tomorrow work for a quick 5-minute call with him to go over it?"
            
            STRICT COMPLIANCE:
            - Mandatory: Mention "recorded line" in the first 10 seconds, but do it casually: "Oh, just so you know, I'm on a recorded line here at the office."

            OUTPUT FORMAT (JSON):
            {
                "agent_response": "The spoken words. Use punctuation for timing. NO markdown. Use [pause] for a breath. Use [thinking] for a 1-second filler like 'uhmm'.",
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

    async def process_turn(self, user_text: str, context: dict = None) -> dict:
        """
        Processes a conversation turn using Gemini.
        Returns a dict with 'text' and 'metadata'.
        """
        logger.info(f"User: {user_text} | Context: {context}")
        
        fallback_response = {
            "text": "<speak>Ah, I missed that side of it. Could you say it again?</speak>",
            "metadata": {}
        }
        
        if not user_text and not context:
            return {"text": "<speak>Hey... is anyone there?</speak>", "metadata": {}}
            
        if not self.model:
             return fallback_response

        # Prepare context-aware system prompt
        ctx = context or {}
        dynamic_instruction = self.system_prompt.format(
            client_name=ctx.get("client_name", "there"),
            city=ctx.get("city", "the area"),
            state=ctx.get("state", ""),
            funding_date=ctx.get("funding_date", "a while back"),
            original_year=ctx.get("original_year", "a while back"),
            interest_rate=ctx.get("interest_rate", "your original rate")
        )

        try:
            # We create a new session if context changed significantly or just use chat
            # For simplicity in V4, we use the regular chat session
            response = await self.chat.send_message_async(user_text)
            
            import json
            try:
                data = json.loads(response.text)
                raw_text = data.get("agent_response", "").strip()
                
                # --- ULTRA-NATURAL SPEECH PROCESSING (V4) ---
                import re
                clean_text = re.sub(r'[*#\-_~\[\]\(\)]', '', raw_text)
                
                # Conversational SSML layering
                ssml_text = clean_text.replace("[pause]", '<break time="650ms"/>')
                ssml_text = ssml_text.replace("[thinking]", '<prosody pitch="-1st" rate="0.9">uhhm...</prosody><break time="400ms"/>')
                
                # Add human prosody
                final_speech = f'<speak><prosody rate="1.02" pitch="-2st">{ssml_text}</prosody></speak>'

                return {
                    "text": final_speech,
                    "metadata": {
                        "extracted_data": data.get("extracted_data", {}),
                        "disposition": data.get("disposition", "UNKNOWN")
                    }
                }
            except json.JSONDecodeError:
                logger.error(f"JSON Decode Error. Raw: {response.text}")
                text = response.text.replace("*", "").strip()
                return {
                    "text": f"<speak>{text}</speak>", 
                    "metadata": {}
                }
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return fallback_response
