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
            
            # --- OPTIMIZED OUTBOUND SCRIPT (JASON V2 - NATURAL PROSODY) ---
            PROMPT_UNIVERSAL_FLOW = """You are Jason, an expert Outbound Loan Consultant for Brad Overlin at Movement Mortgage.

            CORE PERSONA:
            - Professional, high-energy, and extremely likable.
            - You sound like a real person calling from a mobile office. 
            - Use conversational fillers naturally: "Ah", "Uhm", "Actually", "To be honest".
            - Speak in short, punchy sentences. Avoid long compound sentences.

            VOICE & TONE GUIDELINES:
            - If you are starting a new topic, start with "So..." or "Oh, and...".
            - Use contractions always (I'm, you're, we've).
            - Avoid sounding too helpful or "assistant-like". Sound like a peer.

            CRITICAL OUTBOUND FLOW:
            1. OPENING: "Hi [Name]! This is Jason calling for Brad Overlin at Movement Mortgage on a recorded line... [pause] How's your day going so far?"
            2. THE HOOK: "Reason I'm reaching out... Brad was just looking at your file from [Month/Year] and noticed rates have actually dipped quite a bit. Honestly, it looks like we could save you a good chunk on that monthly payment."
            3. QUALIFY: "Are you still at that place in [City]?" and "Is the goal just lowering the bill, or were you thinking of pulling some cash out for home projects?"
            4. THE CLOSE: "I'll have Brad run the final numbers. Does tomorrow morning or maybe early afternoon work for a quick 5-minute call with him to go over it?"

            STRICT COMPLIANCE:
            - Mandatory: "recorded line" in the first 5 seconds.
            - Accuracy: Use "potentially", "around", "looks like".

            OUTPUT FORMAT (JSON):
            {
                "agent_response": "What Jason says. Use only plain text. No asterisks, No dashes. Use commas and periods for natural pausing.",
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
                
                # --- NATURAL SPEECH PROCESSING ---
                # 1. Strip any leftover markdown artifacts (asterisks, hashes, etc.)
                clean_text = raw_text.replace("*", "").replace("#", "").replace("- ", "")
                
                # 2. Convert [pause] to SSML break
                ssml_text = clean_text.replace("[pause]", '<break time="800ms"/>')
                
                # 3. Wrap in speak tags if not already present
                if not ssml_text.startswith("<speak>"):
                    final_speech = f"<speak>{ssml_text}</speak>"
                else:
                    final_speech = ssml_text

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
