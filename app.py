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
    
        logger.info(f"PROCESSED USER TEXT: '{user_text}'")

        # Process with Brain
        # Extract context from session parameters (passed by Dialogflow/GCP)
        session_params = data.get("sessionInfo", {}).get("parameters", {})
        context = {
            "client_name": session_params.get("client_name", session_params.get("telephony-caller-id", "there")),
            "city": session_params.get("city", "your area"),
            "state": session_params.get("state", ""),
            "funding_date": session_params.get("funding_date", ""),
            "original_year": session_params.get("original_year", ""),
            "interest_rate": session_params.get("interest_rate", "")
        }
        
        response_data = await brain.process_turn(user_text or "", context=context)
        agent_text = response_data.get("text", "I'm having a brief glitch.")
        metadata = response_data.get("metadata", {})
        
        # Flatten metadata for Dialogflow Parameters
        parameters = {}
        if "lead" in metadata:
            parameters.update(metadata["lead"])
        if "conversation" in metadata:
            parameters.update(metadata["conversation"])
            
    except Exception as e:
        logger.error(f"CRITICAL WEBHOOK ERROR: {e}")
        agent_text = "I'm having a brief technical glitch. Could you say that again?"
        parameters = {"error": str(e)}

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
        "session_info": {
            "parameters": parameters
        }
    }
    
    return JSONResponse(content=response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
