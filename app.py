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
        # Extract text from Dialogflow CX payload
        # Standard CX format: request -> text
        # Or nested: detectIntentResponse -> queryResult -> text
        user_text = data.get("text")
        
        if not user_text:
            query_result = data.get("detectIntentResponse", {}).get("queryResult", {})
            user_text = query_result.get("text") or query_result.get("transcript")
            
        # Fallback: Check top-level transcript (common in telephony no-match events)
        if not user_text:
            user_text = data.get("transcript")
        
        # If still empty, check for Page/Intent Info (Welcome Event)
        if not user_text:
             intent_info = data.get("detectIntentResponse", {}).get("queryResult", {}).get("intent", {})
             if intent_info.get("displayName") == "Default Welcome Intent":
                 user_text = "Hello"
    
        # Process with Brain
        response_data = await brain.process_turn(user_text or "")
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
