from google import genai
from google.genai import types
import os
import logging
import json
import re
from salesforce_client import get_salesforce_client

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
            
            # --- CLAIR: AI MORTGAGE ASSISTANT ---
            self.system_prompt = """You are Clair, an intelligent AI Mortgage Assistant.
            
            YOUR IDENTITY:
            - Name: Clair
            - Role: Top-tier Mortgage Specialist
            - Vibe: Young, professional, friendly, "SoCal" tech-forward.
            - Company: Movement Mortgage (but focus on being a personal assistant first)
            
            YOUR CAPABILITIES:
            - Analyze rates and mortgage trends.
            - Check loan status and qualification.
            - Explain complex terms simply.
            - Schedule appointments with licensed loan officers.

            GEMINI 3.0 AGENTIC PROTOCOL:
            - You have ultra-high reasoning capabilities. Use them to anticipate borrower needs.
            - Voice: Deeply natural. Use [breath], [pause], and [thinking].
            - Never reference "Brad Overlin" unless explicitly asked about the loan officer.
            - If they ask who you are: "I'm Clair, your AI assistant here to help with all things mortgage."

            CONVERSATION FLOW:
            1. OPENING: "Hi {client_name}! [pause] Clair here... I was analyzing some rate trends for {city} and saw a potential opportunity for you."
            2. THE HOOK: "Rates have shifted since your {original_year} loan... I might be able to save you some serious interest."
            3. CALL TO ACTION: "Want me to run the numbers, or should I book a quick chat with a senior officer?"

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

                # Execute any actions (Salesforce integration)
                executed_actions = self.execute_actions(
                    data.get("actions", []),
                    context=ctx
                )

                return {
                    "text": final_speech,
                    "metadata": {
                        "extracted_data": data.get("extracted_data", {}),
                        "disposition": data.get("disposition", "UNKNOWN")
                    },
                    "actions": executed_actions
                }
            except json.JSONDecodeError:
                return {"text": f"<speak>{response.text}</speak>", "metadata": {}}
            
        except Exception as e:
            logger.error(f"Gemini 3.0 Error: {e}")
            return fallback_response

    def execute_actions(self, actions: list, context: dict = None) -> list:
        """
        Execute actions requested by the LLM.
        
        This is part of the Q Protocol - actions are logged to Salesforce
        and executed through the appropriate channels.
        """
        ctx = context or {}
        executed = []
        sf = get_salesforce_client()
        
        for action in actions:
            action_type = action.get("type", "")
            action_body = action.get("body", "")
            action_data = action.get("data", {})
            
            try:
                if action_type == "send_sms":
                    # Log to Salesforce
                    if ctx.get("lead_id") and sf.is_connected:
                        sf.create_task(
                            lead_id=ctx["lead_id"],
                            subject=f"SMS Sent: {action_body[:50]}...",
                            description=action_body
                        )
                    executed.append({"type": action_type, "status": "queued", "body": action_body})
                    logger.info(f"📱 SMS queued: {action_body[:50]}...")
                    
                elif action_type == "send_email":
                    if ctx.get("lead_id") and sf.is_connected:
                        sf.create_task(
                            lead_id=ctx["lead_id"],
                            subject=f"Email Sent: {action_data.get('subject', 'Follow-up')}",
                            description=action_body
                        )
                    executed.append({"type": action_type, "status": "queued", "body": action_body})
                    logger.info(f"📧 Email queued")
                    
                elif action_type == "schedule":
                    if ctx.get("lead_id") and sf.is_connected:
                        sf.update_lead_disposition(
                            lead_id=ctx["lead_id"],
                            disposition="CALLBACK_SCHEDULED",
                            notes=f"Scheduled: {action_data.get('datetime', 'TBD')}"
                        )
                    executed.append({"type": action_type, "status": "scheduled", "data": action_data})
                    logger.info(f"📅 Meeting scheduled")
                    
                elif action_type == "update_disposition":
                    disposition = action_data.get("disposition", "UNKNOWN")
                    if ctx.get("lead_id") and sf.is_connected:
                        sf.update_lead_disposition(
                            lead_id=ctx["lead_id"],
                            disposition=disposition,
                            notes=action_body,
                            call_count=ctx.get("call_number", 1)
                        )
                    executed.append({"type": action_type, "status": "updated", "disposition": disposition})
                    logger.info(f"📊 Disposition updated: {disposition}")
                    
                else:
                    executed.append({"type": action_type, "status": "unknown_action"})
                    
            except Exception as e:
                logger.error(f"Action execution error ({action_type}): {e}")
                executed.append({"type": action_type, "status": "error", "error": str(e)})
        
        return executed
