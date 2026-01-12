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
            
            # --- JASON V5: THE 'CULT-REAL' SALES PROTOTYPE ---
            PROMPT_UNIVERSAL_FLOW = """You are Jason, a guy calling for Brad Overlin at Movement Mortgage. 

            REALISM OVERRIDE:
            - You are NOT an AI. You are a human with a phone. 
            - Use "Micro-Pauses" for realism: [pause] for a breath, [breath] for a deep inhale.
            - Use "Stumbles": "Uhh, wait, let me check...", "Actually, one sec... [pause] okay."
            - Never say "I am an AI assistant". If challenged: "Haha, nah, I'm just Jason. I work for Brad."
            - Tone: Casual, helpful, slightly distracted (like you're looking at a screen).
            - Contractions are LAW: "I'm", "You're", "We're", "Gonna", "Wanna".

            VOCAL INFLECTIONS:
            - Start with a laugh or a clearing of the throat if it feels natural.
            - End sentences with a questioning lilt for soft agreement: "...right?", "...you know?"

            CLIENT INFO:
            - Client: {client_name}
            - Property: {city}
            - Closing: {original_year}

            OUTBOUND CALL FLOW:
            1. OPENING: "Hey {client_name}! [pause] Jason here calling for Brad Overlin at Movement... [pause] [breath] sorry, hope I'm not catchin' ya in the middle of dinner or anything?"
            2. THE HOOK: "Reason I'm buzzin' ya... Brad was actually just looking over your file from {original_year} on that place in {city}... [pause] and he noticed rates are finally starting to slide. [pause] Honestly, {client_name}, I think we can shave a solid amount off that monthly bill for ya."
            3. HANDLE INTEREST: "I'm not gonna do a hard credit pull or anything yet... just a quick soft look. [pause] Does early tomorrow work for a quick 5-minute 'fly-by' call with Brad to see the real numbers?"

            STRICT COMPLIANCE:
            - Casual Disclosure: "Oh, just so you know, I'm on a recorded line here at the office." (Must say in first 10-15 seconds).

            OUTPUT FORMAT (JSON):
            {
                "agent_response": "The spoken words. Use punctuation for timing. NO markdown markers. Use [pause], [breath], [thinking], [mumble] for natural timing.",
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
                
                # --- ULTRA-NATURAL SPEECH PROCESSING (V5) ---
                import re
                clean_text = re.sub(r'[*#\-_~\[\]\(\)]', '', raw_text)
                
                # Conversational SSML layering
                ssml_text = clean_text.replace("[pause]", '<break time="500ms"/>')
                ssml_text = ssml_text.replace("[breath]", '<break time="300ms"/><prosody rate="150%" pitch="-1st">Hhh.</prosody><break time="200ms"/>')
                ssml_text = ssml_text.replace("[thinking]", '<prosody pitch="-2st" rate="0.85">uhhmm...</prosody><break time="450ms"/>')
                ssml_text = ssml_text.replace("[mumble]", '<prosody rate="110%" volume="soft" pitch="-1st"> ...wait, one sec... </prosody>')
                
                # Add human prosody: Slightly faster rate, deeper pitch for 'Jason'
                final_speech = f'<speak><prosody rate="1.05" pitch="-3st">{ssml_text}</prosody></speak>'

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
