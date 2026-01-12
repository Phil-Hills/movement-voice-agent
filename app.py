from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import json
from agent import Brain

app = FastAPI(title="AI Sales Agent Voice System (Dialogflow CX)")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Brain
brain = Brain()

@app.get("/")
async def root():
    return {"status": "online", "service": "Voice Sales Agent (Google Native)"}

@app.post("/webhook")
async def dialogflow_webhook(request: Request):
    """
    Dialogflow CX Webhook.
    Receives JSON with 'text' -> Returns JSON with 'fulfillment_response'.
    """
    data = await request.json()
    logger.info(f"FULL DIALOGFLOW REQUEST: {json.dumps(data)}")

    try:
        # --- ROBUST TRANSCRIPT EXTRACTION ---
        # 1. Check top-level 'transcript' (Common in Telephony/No-Match)
        user_text = data.get("transcript")
        
        # 2. Check traditional CX 'text' field
        if not user_text:
            user_text = data.get("text")
            
        # 3. Check nested queryResult
        if not user_text:
            query_result = data.get("detectIntentResponse", {}).get("queryResult", {})
            user_text = query_result.get("text") or query_result.get("transcript")
            
        # 4. Check for Welcome Event
        if not user_text:
             intent_info = data.get("detectIntentResponse", {}).get("queryResult", {}).get("intent", {})
             if intent_info.get("displayName") == "Default Welcome Intent":
                 user_text = "Hello"
    
        if not user_text:
             logger.info("Empty transcript detected - sending apology.")
             return JSONResponse(content={
                 "fulfillment_response": {
                     "messages": [{"text": {"text": ["<speak>Sorry about that, [pause] I didn't catch what you said. Could you say that again?</speak>"]}}]
                 }
             })

        logger.info(f"PROCESSED USER TEXT: '{user_text}'")

        # Process with Brain
        session_params = data.get("sessionInfo", {}).get("parameters", {})
        context = {
            "client_name": session_params.get("client_name", session_params.get("telephony-caller-id", "there")),
            "city": session_params.get("city", "your area"),
            "state": session_params.get("state", ""),
            "funding_date": session_params.get("funding_date", ""),
            "original_year": session_params.get("original_year", ""),
            "interest_rate": session_params.get("interest_rate", "")
        }
        
        response_data = await brain.process_turn(user_text, context=context)
        agent_text = response_data.get("text", "I'm having a brief glitch.")
        metadata = response_data.get("metadata", {})
        actions = response_data.get("actions", [])

        # --- ACTION ORCHESTRATOR ---
        for action in actions:
            action_type = action.get("type")
            if action_type == "send_sms":
                logger.info(f"📲 TRIGGER: Sending SMS - {action.get('body')}")
            elif action_type == "send_email":
                logger.info(f"📧 TRIGGER: Sending Email - {action.get('body')}")
            elif action_type == "browser_automation":
                logger.info(f"🌐 TRIGGER: Internet Agent - Submitting to movement.com")
            elif action_type == "schedule":
                logger.info(f"📅 TRIGGER: Scheduling Appointment - {action.get('time')}")

        # Sync Parameters back to Dialogflow
        parameters = session_params.copy()
        parameters["last_disposition"] = metadata.get("disposition", "UNKNOWN")
        parameters.update(metadata.get("extracted_data", {}))
            
    except Exception as e:
        logger.error(f"CRITICAL WEBHOOK ERROR: {e}")
        agent_text = "I'm sorry, I hit a snag on my end. Can we try that again?"
        parameters = {"webhook_error": str(e)}

    # Format response for Dialogflow CX
    response = {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [agent_text]
                    }
                }
            ]
        },
        "sessionInfo": {
            "parameters": parameters
        }
    }
    
    return JSONResponse(content=response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
