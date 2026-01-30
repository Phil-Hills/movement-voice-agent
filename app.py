from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging
import json
import os
import httpx
from agent import Brain
from salesforce_client import get_salesforce_client
from campaign_manager import get_campaign_manager

app = FastAPI(title="Clair - AI Mortgage Assistant")

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "sk_d640ca46e262d1379cc8e54cfd90cdcf638e9503adb12cae")
# Rachel voice - young, friendly American female (perfect for SoCal vibe)
ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize singletons
brain = Brain()
sf_client = get_salesforce_client()
campaign_manager = get_campaign_manager()


# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the demo landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the protected dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "online", "service": "Voice Sales Agent (Google Native)"}

@app.post("/demo")
async def demo_chat(request: Request):
    """Demo endpoint for the web chat interface"""
    data = await request.json()
    user_text = data.get("text", "")
    
    if not user_text:
        return JSONResponse(content={"text": "I didn't catch that. Could you say it again?"})
    
    # Get context from frontend (includes memory brain identity)
    frontend_context = data.get("context", {})
    
    # Merge with default demo context if keys missing
    context = {
        "client_name": "Demo User",
        "city": "Seattle",
        "original_year": "2023",
        **frontend_context  # Frontend overrides defaults
    }
    response_data = await brain.process_turn(user_text, context=context)
    return JSONResponse(content=response_data)
    



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


# =========================================================================
# SALESFORCE API ENDPOINTS
# =========================================================================

@app.get("/api/dashboard/stats")
async def dashboard_stats():
    """Get real-time dashboard statistics from Salesforce"""
    return JSONResponse(content=sf_client.get_dashboard_stats())

@app.get("/api/dashboard/leads")
async def dashboard_leads():
    """Get recent leads activity from Salesforce"""
    leads = sf_client.get_recent_leads(limit=10)
    return JSONResponse(content={"leads": leads})

@app.get("/api/salesforce/status")
async def salesforce_status():
    """Check Salesforce connection status"""
    return {
        "connected": sf_client.is_connected,
        "mode": "live" if sf_client.is_connected else "demo"
    }

@app.get("/api/salesforce/lead/{lead_id}")
async def get_lead(lead_id: str):
    """Get lead data from Salesforce"""
    lead = sf_client.get_lead(lead_id)
    if lead:
        return JSONResponse(content={"success": True, "lead": lead})
    return JSONResponse(content={"success": False, "error": "Lead not found"}, status_code=404)

@app.post("/api/salesforce/lead/{lead_id}/call")
async def process_lead_call(lead_id: str, request: Request):
    """
    Process a call for a specific lead.
    Uses Salesforce data to personalize the conversation.
    """
    data = await request.json()
    user_text = data.get("text", "")
    call_number = data.get("call_number", 1)
    
    # Get lead data from Salesforce
    lead = sf_client.get_lead(lead_id)
    
    if not lead:
        return JSONResponse(
            content={"error": "Lead not found"},
            status_code=404
        )
    
    # Build context from Salesforce data
    context = {
        "lead_id": lead_id,
        "client_name": f"{lead.get('FirstName', 'there')}",
        "city": lead.get("City", "your area"),
        "original_year": lead.get("Original_Year__c", "2023"),
        "call_number": call_number
    }
    
    # Process with Gemini
    response_data = await brain.process_turn(user_text, context=context)
    
    # Log the call to Salesforce
    if sf_client.is_connected:
        sf_client.log_call(
            lead_id=lead_id,
            call_outcome=response_data.get("metadata", {}).get("disposition", "IN_PROGRESS"),
            duration_seconds=0,  # Would come from actual call
            notes=f"User: {user_text}\nAgent: {response_data.get('text', '')[:500]}",
            call_number=call_number
        )
    
    return JSONResponse(content=response_data)


# =========================================================================
# CAMPAIGN / DIALER ENDPOINTS
# =========================================================================

@app.post("/api/campaigns/upload")
async def upload_campaign(file: UploadFile = File(...)):
    """Upload a CSV list for outbound dialing"""
    content = await file.read()
    result = await campaign_manager.load_campaign_from_csv(content.decode('utf-8'))
    return JSONResponse(content=result)

@app.post("/api/campaigns/import-salesforce")
async def import_salesforce_campaign(request: Request):
    """Import leads directly from a Salesforce Campaign"""
    data = await request.json()
    campaign_id = data.get("campaign_id")
    if not campaign_id:
        return JSONResponse(content={"success": False, "error": "Missing campaign_id"}, status_code=400)
        
    result = await campaign_manager.load_campaign_from_salesforce(campaign_id)
    return JSONResponse(content=result)

@app.post("/api/campaigns/start")
async def start_campaign():
    """Start the outbound dialer"""
    await campaign_manager.start_campaign()
    return JSONResponse(content={"status": "started"})

@app.post("/api/campaigns/stop")
async def stop_campaign():
    """Stop the outbound dialer"""
    await campaign_manager.stop_campaign()
    return JSONResponse(content={"status": "stopped"})

@app.get("/api/campaigns/status")
async def campaign_status():
    """Get current dialer status and stats"""
    return JSONResponse(content={
        "active": campaign_manager.is_running,
        "stats": campaign_manager.stats,
        "current_index": campaign_manager.current_lead_index,
        "total": len(campaign_manager.active_campaign)
    })


@app.post("/api/auth/login")
async def login(request: Request):
    """Simple auth endpoint for demo login"""
    data = await request.json()
    email = data.get("email", "")
    # In production, validate against Firebase/Auth0
    # For demo, just return success
    return JSONResponse(content={
        "success": True,
        "token": "demo_token",
        "user": {"email": email}
    })


# =========================================================================
# ELEVENLABS TEXT-TO-SPEECH
# =========================================================================

@app.api_route("/api/tts", methods=["GET", "POST"])
async def text_to_speech(request: Request):
    """
    Convert text to speech using ElevenLabs premium voices.
    Returns audio/mpeg stream for playback.
    """
    if request.method == "GET":
        text = request.query_params.get("text", "")
    else:
        try:
            data = await request.json()
            text = data.get("text", "")
        except:
            text = ""
    
    if not text:
        return JSONResponse(content={"error": "No text provided"}, status_code=400)
    
    # Clean SSML tags for ElevenLabs (it uses its own format)
    import re
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # ElevenLabs API call
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    payload = {
        "text": clean_text,
        "model_id": "eleven_turbo_v2_5",  # Newer, more natural model
        "voice_settings": {
            "stability": 0.4,       # Lower stability = more natural variation
            "similarity_boost": 0.75,
            "style": 0.5,           # Higher style = more expressive/emotional
            "use_speaker_boost": True
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                return StreamingResponse(
                    iter([response.content]),
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": "inline; filename=speech.mp3"}
                )
            else:
                logger.error(f"ElevenLabs error: {response.status_code} - {response.text}")
                return JSONResponse(
                    content={"error": "TTS failed", "details": response.text},
                    status_code=response.status_code
                )
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
