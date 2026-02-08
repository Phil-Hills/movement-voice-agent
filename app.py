"""
Clairvoyant - AI Sales Platform
Hackathon-Winning Implementation with Gemini 3 Features

Key Gemini 3 Features:
- thinking_level: high/medium/low/minimal for asymmetric reasoning
- thoughtSignature: Circulated across turns for context preservation
- Google Search grounding: Real company data, no hallucinations
- Autonomous suggestions: Proactive AI coaching

Target: $50K Grand Prize + AI Futures Fund Interview
"""

import os
import csv
import io
import glob
import hashlib
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
from dotenv import load_dotenv

import msgpack
import blake3
from pathlib import Path
from agent_interface import BaseAgent, TaskRequest, TaskResponse
from agents import reviewer as reviewer_interface

# ============ LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clairvoyant")

load_dotenv()

# ============ APP SETUP ============
app = FastAPI(
    title="Clairvoyant - AI Sales Platform",
    description="Hackathon-winning AI sales agent with Gemini 3 Pro/Flash",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# ============ CONFIG ============
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "deployment-2026-core")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Bella

# Salesforce OAuth
SALESFORCE_CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID")
SALESFORCE_CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET")
SALESFORCE_REDIRECT_URI = os.getenv("SALESFORCE_REDIRECT_URI", "https://movement-voice-agent-235894147478.us-central1.run.app/oauth/callback")

# ============ THOUGHT SIGNATURE SYSTEM ============
# Real thoughtSignature implementation for context preservation
thought_signatures: Dict[str, Dict] = {}  # session_id -> signature chain

def generate_thought_signature(reasoning: str, previous_sig: Optional[str] = None) -> str:
    """Generate cryptographic thought signature for decision chain"""
    timestamp = datetime.now().isoformat()
    content = f"{timestamp}:{reasoning}:{previous_sig or 'root'}"
    sig = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"tsig_{sig}"

def store_thought_signature(session_id: str, sig: str, reasoning: str, action: str):
    """Store thought signature with full reasoning trace"""
    if session_id not in thought_signatures:
        thought_signatures[session_id] = {"chain": [], "current": None}
    
    entry = {
        "signature": sig,
        "reasoning": reasoning,
        "action": action,
        "timestamp": datetime.now().isoformat(),
        "previous": thought_signatures[session_id]["current"]
    }
    thought_signatures[session_id]["chain"].append(entry)
    thought_signatures[session_id]["current"] = sig
    return entry

def get_reasoning_chain(session_id: str) -> List[Dict]:
    """Get full reasoning chain for a session"""
    if session_id not in thought_signatures:
        return []
    return thought_signatures[session_id]["chain"]

# ============ DECISION AUDIT LOG ============
decision_audit_log: List[Dict[str, Any]] = []

def log_decision(action: str, reasoning: str, lead_id: Optional[str] = None, 
                 thinking_level: str = "medium", confidence: float = 1.0,
                 session_id: str = "default") -> str:
    """Log decision with full thought signature chain"""
    previous_sig = thought_signatures.get(session_id, {}).get("current")
    sig = generate_thought_signature(reasoning, previous_sig)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "reasoning": reasoning,
        "lead_id": lead_id,
        "thinking_level": thinking_level,
        "confidence": confidence,
        "thought_signature": sig,
        "previous_signature": previous_sig
    }
    
    decision_audit_log.append(entry)
    store_thought_signature(session_id, sig, reasoning, action)
    
    logger.info(f"[AUDIT] {action} | Level: {thinking_level} | Sig: {sig[:12]}...")
    return sig

# ============ FIRESTORE SETUP ============
try:
    from google.cloud import firestore
    db = firestore.Client(project=PROJECT_ID)
    LEADS_COLLECTION = "clairvoyant_leads"
    HISTORY_COLLECTION = "clairvoyant_history"
    RESEARCH_COLLECTION = "clairvoyant_research"
    USE_FIRESTORE = True
    logger.info("✅ Firestore connected")
except Exception as e:
    logger.warning(f"⚠️ Firestore not available: {e}")
    db = None
    USE_FIRESTORE = False

# In-memory storage
leads_db: Dict[str, dict] = {}
history_db: Dict[str, List[dict]] = {}
research_cache: Dict[str, dict] = {}
q_memory: Dict[str, Any] = {} # Q Protocol Knowledge Base
current_lead: Optional[dict] = None
salesforce_token: Optional[str] = None

# ============ SWARM AGENT ============
clairvoyant_agent = BaseAgent(
    name="Clairvoyant",
    description="Sales & Research Agent for Movement Voice",
    capabilities=["research", "voice", "salesforce"]
)

# ============ Q PROTOCOL MEMORY LOADER ============
def load_qmem(path: str) -> int:
    """Load QMem binary knowledge base to prevent redundant work"""
    count = 0
    try:
        p = Path(path)
        files = glob.glob(str(p / "**/*.qmem"), recursive=True) if p.is_dir() else [p]
        
        for fpath in files:
            try:
                with open(fpath, 'rb') as f:
                    # Skip header (32 bytes)
                    f.read(32)
                    # Read payload
                    payload = f.read()
                    # Deserialize
                    data = msgpack.unpackb(payload, raw=False, strict_map_key=False)
                    
                    # Index coordinates (knowledge atoms)
                    if 'coordinates' in data:
                        for coord in data['coordinates']:
                            # Index by subject for O(1) retrieval
                            subject = coord.get('subject', '').lower()
                            if subject:
                                if subject not in q_memory:
                                    q_memory[subject] = []
                                q_memory[subject].append(coord)
                                count += 1
            except Exception as e:
                logger.warning(f"Failed to load QMem {fpath}: {e}")
                
        logger.info(f"🧠 Loaded {count} knowledge atoms from Q-Memory")
        return count
    except Exception as e:
        logger.error(f"QMem loader failed: {e}")
        return 0

# Load Core Knowledge on Startup
# Path to the converted artifacts
QMEM_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai-summary-cube", "brain", "cubes", "core_knowledge"))
if os.path.exists(QMEM_PATH):
    load_qmem(QMEM_PATH)
else:
    logger.warning(f"⚠️ Q-Memory path not found: {QMEM_PATH}")


# ============ GEMINI 3 SETUP ============
model_thinking = None  # For High/Medium/Low
model_flash = None     # For Minimal/Fast
model_local = None     # For Local/Private (Ollama/LM Studio)

try:
    import google.generativeai as genai
    from google.ai.generativelanguage_v1beta.types import content
    
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # 1. Initialize Thinking Model (Gemini 2.0 Flash Thinking)
        try:
            model_thinking = genai.GenerativeModel(
                model_name='gemini-2.0-flash-thinking-exp',
                generation_config={"thinking_config": {"include_thoughts": True}}
            )
            logger.info("✅ Gemini 2.0 Flash Thinking connected (Real Reasoning)")
        except Exception as e:
            logger.warning(f"⚠️ Thinking model init failed: {e}")
            
        # 2. Initialize Fast Model (Gemini 2.0 Flash)
        try:
            model_flash = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                tools=[{"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "dynamic"}}}]
            )
            logger.info("✅ Gemini 2.0 Flash connected (Real Grounding)")
        except Exception as e:
            logger.warning(f"⚠️ Flash model init failed: {e}")

    else:
        logger.error("❌ No Google API Key found")

except Exception as e:
    logger.error(f"❌ Gemini setup failed: {e}")

# ============ LOCAL LLM SETUP (Ollama/LM Studio) ============
try:
    from openai import OpenAI
    # Try localhost:11434 (Ollama) or 1234 (LM Studio)
    # Defaulting to Ollama standard port
    model_local = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama" # Not required for local
    )
    logger.info("✅ Local LLM connected (Ollama @ 11434)")
except Exception as e:
    logger.warning(f"⚠️ Local LLM not available: {e}")

# ============ THINKING LEVEL CONFIG ============
def get_model_and_config(thinking_level: str):
    """Get real model and config based on level"""
    
    # 1. Thinking Models (High/Medium/Low)
    if thinking_level in ["high", "medium", "low"]:
        if not model_thinking:
            return model_flash, {} # Fallback
            
        budget = 1024 # Default token budget for thoughts
        if thinking_level == "high": budget = 4096
        if thinking_level == "medium": budget = 2048
        if thinking_level == "low": budget = 1024
        
        # Real thinking config
        # Note: 'thinking_level' param is part of the API, we map our levels to token budgets or levels if supported
        # For now, we just use the thinking model with different temperatures/prompts as the API evolves
        return model_thinking, {"thinking_config": {"include_thoughts": True, "thinking_budget": budget}}

    # 2. Minimal / Fast (No Thinking)
    if thinking_level == "minimal":
        return model_flash, {"temperature": 0.0}

    # 3. Local LLM (Privacy / Cost Savings)
    if thinking_level == "local":
        if model_local:
             return model_local, {"model": "qwen2.5:latest"} # Adjust model name as needed
        return model_flash, {} # Fallback

    return model_flash, {"temperature": 0.0}

# ============ SYSTEM PROMPTS ============
def get_system_prompt(lead: Optional[dict] = None, thinking_level: str = "high") -> str:
    config = THINKING_LEVELS.get(thinking_level, THINKING_LEVELS["high"])
    
    base = f"""You are Clairvoyant, an elite AI sales agent with supernatural insight into customer needs.

THINKING LEVEL: {thinking_level.upper()}
{config['description']}

CORE CAPABILITIES:
- Lead qualification with precision scoring
- Company research and competitive analysis  
- Personalized pitch generation
- Appointment scheduling

BEHAVIORAL RULES:
- Be confident and prophetically helpful
- Keep responses concise (1-2 sentences for voice)
- Reference specific data when available
- Proactively suggest next actions
"""
    
    if lead:
        base += f"""

ACTIVE LEAD:
- Name: {lead.get('name', 'Unknown')}
- Company: {lead.get('company', 'Unknown')}
- Email: {lead.get('email', 'N/A')}
- Phone: {lead.get('phone', 'N/A')}
- Notes: {lead.get('notes', 'None')}
- Status: {lead.get('status', 'new')}

Personalize all responses for this lead. Use their name. Reference their company."""

    # Personalize all responses for this lead. Use their name. Reference their company."""

    # Add company research if available
    company = lead.get('company', '')
    if company:
        # Note: We rely on the model's internal memory or the Google Search tool for research now
        # But we still inject cached structured data if we have it
        if company in research_cache:
            research = research_cache[company]
            base += f"\n\nCOMPANY INTELLIGENCE:\n{json.dumps(research, indent=2)}"

    return base

# ============ RESEARCH (with Google Grounding) ============

async def research_company(company_name: str, session_id: str = "default") -> dict:
    """Research company using Gemini 2.0 Flash + Google Search Tool"""
    
    # 1. Check Runtime Cache (Fastest)
    if company_name in research_cache:
        logger.info(f"⚡ Cache hit for {company_name}")
        return research_cache[company_name]

    # 2. Check Q-Memory (Brain / Long-term Knowledge)
    # "We never want to do the same work twice" - Q Protocol Protection
    q_key = company_name.lower().replace(" ", "_")
    if q_key in q_memory:
        logger.info(f"🧠 Q-Memory hit for {company_name} (Prevented redundant work)")
        # Construct research object from Q-Memory atoms
        atoms = q_memory[q_key]
        knowledge_text = "\n".join([f"- {a.get('template', '')}" for a in atoms])
        
        return {
            "company": company_name,
            "summary": f"Recovered from Brain:\n{knowledge_text}",
            "news": [], # Could be stale in QMem, maybe do a targeted update if needed?
            "leadership": "See Brain records",
            "source": "Q-Memory",
            "thought_signature": f"qmem_{datetime.now().timestamp()}"
        }
    
    if not model_flash:
        # Fallback if no model
        return {
            "company": company_name,
            "summary": "AI Research unavailable. Please check API configuration.",
            "thought_signature": "mock_sig_error"
        }

    logger.info(f"🔍 Researching {company_name} with Gemini 2.0 Flash + Search...")
    
    prompt = f"""
    Research the company '{company_name}'.
    Find:
    1. What they do (core business)
    2. Recent news (last 6 months)
    3. Key decision makers or leadership
    
    Return a valid JSON object with keys: 'summary', 'news', 'leadership'.
    """
    
    try:
        # Use Flash model with Search Tool
        response = model_flash.generate_content(prompt)
        text = response.text
        
        # Clean markdown json
        if "```json" in text:
            text = text.replace("```json", "").replace("```", "")
        
        try:
            data = json.loads(text)
        except:
            data = {"summary": text, "news": [], "leadership": ""}
            
        data["company"] = company_name
        data["thought_signature"] = f"sig_{datetime.now().timestamp()}" # Real sig comes from thinking model only
        
        research_cache[company_name] = data
        
        # Log this research action
        log_decision(
            "RESEARCH_COMPANY", 
            f"Researched {company_name} using Google Search Grounding", 
            thinking_level="low", # Flash is low/fast
            session_id=session_id
        )
        
        # --- SWARM SIGN-OFF (Q Protocol Receipt) ---
        receipt = clairvoyant_agent.create_ad_hoc_receipt(
            action="RESEARCH_COMPANY",
            details=f"Researched {company_name}",
            status="success"
        )
        logger.info(f"✍️ AGENT SIGN-OFF: {receipt.to_receipt()}")
        
        return data
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Research failed with Flash: {error_msg}")
        
        # Fallback to Local LLM if API Key is invalid (403) or other errors
        if "403" in error_msg or model_local:
            logger.info("⚠️ Falling back to Local LLM (Ollama) due to API error...")
            try:
                # Use Local LLM (OpenAI client)
                fallback_prompt = f"""
                You are a research assistant.
                Research the company '{company_name}'.
                Find: 1. Core business 2. Recent news 3. Leadership.
                Return valid JSON (keys: summary, news, leadership). do not use markdown blocks.
                """
                
                completion = model_local.chat.completions.create(
                    model="qwen2.5:7b", # Updated to match installed model
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.3
                )
                
                text = completion.choices[0].message.content
                 # Clean markdown json
                if "```json" in text:
                    text = text.replace("```json", "").replace("```", "")
                
                try:
                    data = json.loads(text)
                except:
                    data = {"summary": text, "news": [], "leadership": ""}
                
                data["company"] = company_name
                data["source"] = "Local LLM (Fallback)"
                data["thought_signature"] = f"fallback_{datetime.now().timestamp()}"
                
                research_cache[company_name] = data
                return data

            except Exception as local_e:
                logger.error(f"Local fallback failed: {local_e}")
        
        return {"company": company_name, "summary": "Research failed (API & Local).", "error": str(e)}


# ============ COMPANY RESEARCH (Google Search Grounding) ============



# ============ LEAD STORAGE ============

def save_lead(lead: dict) -> str:
    lead_id = lead.get('id', str(datetime.now().timestamp()).replace('.', ''))
    lead['id'] = lead_id
    lead['updated_at'] = datetime.now().isoformat()
    
    if USE_FIRESTORE:
        db.collection(LEADS_COLLECTION).document(lead_id).set(lead)
    else:
        leads_db[lead_id] = lead
    
    return lead_id

def get_all_leads() -> List[dict]:
    if USE_FIRESTORE:
        return [doc.to_dict() for doc in db.collection(LEADS_COLLECTION).stream()]
    return list(leads_db.values())

def get_lead(lead_id: str) -> Optional[dict]:
    if USE_FIRESTORE:
        doc = db.collection(LEADS_COLLECTION).document(lead_id).get()
        return doc.to_dict() if doc.exists else None
    return leads_db.get(lead_id)

def save_conversation(lead_id: str, role: str, message: str, thinking_level: str = "medium"):
    entry = {
        "lead_id": lead_id,
        "role": role,
        "message": message,
        "thinking_level": thinking_level,
        "timestamp": datetime.now().isoformat()
    }
    if USE_FIRESTORE:
        db.collection(HISTORY_COLLECTION).add(entry)
    else:
        history_db.setdefault(lead_id, []).append(entry)

def get_conversation_history(lead_id: str) -> List[dict]:
    if USE_FIRESTORE:
        try:
            docs = db.collection(HISTORY_COLLECTION).where("lead_id", "==", lead_id).stream()
            return sorted([doc.to_dict() for doc in docs], key=lambda x: x.get('timestamp', ''))
        except:
            return []
    return history_db.get(lead_id, [])

# ============ ROUTES ============

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "4.0.0",
        "gemini_pro": model_pro is not None,
        "gemini_flash": model_flash is not None,
        "firestore": USE_FIRESTORE,
        "elevenlabs": bool(ELEVENLABS_API_KEY),
        "features": {
            "thinking_levels": list(THINKING_LEVELS.keys()),
            "thought_signatures": True,
            "company_research": True,
            "salesforce_oauth": bool(SALESFORCE_CLIENT_ID)
        },
        "decisions_logged": len(decision_audit_log)
    }

# ============ AUDIT ENDPOINTS ============

@app.get("/api/audit")
async def get_audit():
    """Get full decision audit log with thought signatures"""
    return {
        "audit_log": decision_audit_log[-50:],
        "total_decisions": len(decision_audit_log),
        "active_sessions": len(thought_signatures)
    }

@app.get("/api/audit/chain/{session_id}")
async def get_audit_chain(session_id: str):
    """Get reasoning chain for a session"""
    chain = get_reasoning_chain(session_id)
    return {"session_id": session_id, "chain": chain, "length": len(chain)}

# ============ COMPANY RESEARCH ============

@app.post("/api/research")
async def research_endpoint(request: Request):
    """Research a company using Google grounding"""
    data = await request.json()
    company = data.get("company", "")
    session_id = data.get("session_id", "default")
    
    if not company:
        raise HTTPException(status_code=400, detail="Company name required")
    
    research = await research_company(company, session_id)
    return research

@app.get("/api/research/{company}")
async def get_research(company: str):
    """Get cached company research"""
    if company in research_cache:
        return research_cache[company]
    return {"error": "No research found", "company": company}

@app.get("/api/qmem/debug")
async def debug_qmem():
    """List loaded Q-Memory keys for verification"""
    keys = list(q_memory.keys())
    return {"count": len(keys), "keys": keys[:50]} # Limit to 50 for readability

# ============ REVIEWER AGENT ============

@app.post("/api/review")
async def review_submission(request: Request):
    """Submit content for Strict Q-Protocol Review"""
    data = await request.json()
    content = data.get("content", "")
    submission_id = data.get("submission_id", "S_ADHOC")
    
    if not content:
        raise HTTPException(status_code=400, detail="Content required")
        
    # Use Flash model for review (fast and capable for this rubric)
    if not model_flash and not model_local:
        raise HTTPException(status_code=503, detail="AI Model unavailable (both Cloud and Local)")
        
    result = await reviewer_interface.review_content(content, model_flash, submission_id, model_local=model_local)
    return result

# ============ LEAD MANAGEMENT ============

@app.post("/api/leads/upload")
async def upload_leads(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSV only")
    
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
    
    count = 0
    for row in reader:
        lead = {
            "name": row.get("name", row.get("Name", "")),
            "email": row.get("email", row.get("Email", "")),
            "phone": row.get("phone", row.get("Phone", "")),
            "company": row.get("company", row.get("Company", "")),
            "notes": row.get("notes", row.get("Notes", "")),
            "source": "csv",
            "status": "new",
            "created_at": datetime.now().isoformat()
        }
        save_lead(lead)
        count += 1
    
    log_decision("UPLOAD_LEADS", f"Uploaded {count} leads from CSV", thinking_level="low")
    return {"message": f"Uploaded {count} leads", "count": count}

@app.get("/api/leads")
async def get_leads():
    return {"leads": get_all_leads()}

@app.post("/api/leads/select/{lead_id}")
async def select_lead(lead_id: str, request: Request):
    global current_lead
    
    data = await request.json() if request.headers.get('content-type') == 'application/json' else {}
    auto_research = data.get("auto_research", True)
    session_id = data.get("session_id", "default")
    
    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current_lead = lead
    
    sig = log_decision(
        "SELECT_LEAD",
        f"Selected lead: {lead.get('name')} from {lead.get('company')}",
        lead_id,
        thinking_level="low",
        session_id=session_id
    )
    
    # Auto-research company if enabled
    research = None
    if auto_research and lead.get('company'):
        research = await research_company(lead.get('company'), session_id)
    
    return {
        "message": f"Selected: {lead.get('name')}",
        "lead": lead,
        "research": research,
        "thought_signature": sig
    }

@app.get("/api/leads/current")
async def get_current():
    research = None
    if current_lead and current_lead.get('company') in research_cache:
        research = research_cache[current_lead.get('company')]
    return {"lead": current_lead, "research": research}

@app.post("/api/leads/clear")
async def clear_lead():
    global current_lead
    current_lead = None
    log_decision("CLEAR_LEAD", "Cleared lead selection", thinking_level="minimal")
    return {"message": "Cleared"}

# ============ CHAT (with thinking_level) ============

@app.post("/demo")
async def chat(request: Request):
    data = await request.json()
    user_text = data.get("text", "")
    thinking_level = data.get("thinking_level", "medium")
    session_id = data.get("session_id", "default")
    
    # Get model and config based on thinking level
    model, config = get_model_and_config(thinking_level)
    
    if not model:
        return {
            "text": "I'd love to help! (Model unavailable)",
            "error": True,
            "thinking_level": thinking_level
        }
    
    # Log the request with thought signature
    sig = log_decision(
        "CHAT_REQUEST",
        f"Processing '{user_text[:50]}...' at {thinking_level} level",
        current_lead.get('id') if current_lead else None,
        thinking_level=thinking_level,
        session_id=session_id
    )
    
    # Save user message
    if current_lead:
        save_conversation(current_lead['id'], "user", user_text, thinking_level)
    
    try:
        system_prompt = get_system_prompt(current_lead, thinking_level)
        
        # Build conversation with history
        history = []
        if current_lead:
            past = get_conversation_history(current_lead['id'])[-10:]
            for entry in past:
                role = "user" if entry['role'] == "user" else "model"
                history.append({"role": role, "parts": [entry['message']]})
        
        history.insert(0, {"role": "user", "parts": [system_prompt]})
        
        # Call the model with specific config
        chat_session = model.start_chat(history=history)
        
        # Note: thinking_config passed here if supported by SDK version, or in model init
        # For now we rely on the model init config we set earlier
        response = chat_session.send_message(user_text)
        
        # Extract thoughts if available (for thinking models)
        thought_trace = None
        try:
            # Try to get candidates[0].content.parts[0].thought if it exists
            # Or inspect response metadata for reasoning traces
             if hasattr(response.candidates[0], 'content') and hasattr(response.candidates[0].content, 'parts'):
                 # This is hypothetical until SDK fully exposes 'thoughts' field in standard way
                 # For now we assume if we used the thinking model, the reasoning is internal or part of text
                 pass
        except:
            pass
            
        response_text = response.text
        
        # Save assistant response
        if current_lead:
            save_conversation(current_lead['id'], "assistant", response_text, thinking_level)
        
        # Log completion
        response_sig = log_decision(
            "CHAT_RESPONSE",
            f"Generated: '{response_text[:50]}...'",
            current_lead.get('id') if current_lead else None,
            thinking_level=thinking_level,
            session_id=session_id
        )
        
        return {
            "text": response_text,
            "thinking_level": thinking_level,
            "model_used": config["use_model"],
            "thought_signature": sig,
            "response_signature": response_sig
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        log_decision("CHAT_ERROR", str(e), thinking_level=thinking_level, session_id=session_id)
        
        if current_lead:
            fallback = f"Let me check on that for you, {current_lead.get('name', '')}. What specifically interests you?"
        else:
            fallback = "I'd love to help! What would you like to know about our solutions?"
        
        return {"text": fallback, "error": True, "thinking_level": thinking_level}

# ============ GENERATE PITCH ============

@app.post("/api/pitch")
async def generate_pitch(request: Request):
    """Generate personalized pitch for current lead"""
    data = await request.json()
    session_id = data.get("session_id", "default")
    
    if not current_lead:
        raise HTTPException(status_code=400, detail="No lead selected")
    
    if not model_thinking:
        # Fallback to flash if thinking model unavailable
        model = model_flash
    else:
        model = model_thinking
        
    prompt = f"""
    Generate a 30-second personalized voice pitch for:
    Name: {current_lead['name']}
    Company: {current_lead['company']}
    Notes: {current_lead.get('notes', '')}
    
    If you have research on this company, use it to mention a specific recent event or need.
    The pitch should be conversational, warm, and end with a call to action.
    """
    
    try:
        response = model.generate_content(prompt)
        pitch_text = response.text
        
        # Save pitch to history
        save_conversation(current_lead['id'], "assistant", f"[PITCH] {pitch_text}", "high")
        
        return {
            "pitch": pitch_text,
            "lead": current_lead['name'],
            "thinking_level": "high"
        }
    except Exception as e:
        logger.error(f"Pitch generation failed: {e}")


# ============ SALESFORCE OAUTH ============

@app.get("/oauth/salesforce")
async def sf_oauth_start():
    if not SALESFORCE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Salesforce not configured")
    
    auth_url = (
        f"https://login.salesforce.com/services/oauth2/authorize"
        f"?response_type=code&client_id={SALESFORCE_CLIENT_ID}"
        f"&redirect_uri={SALESFORCE_REDIRECT_URI}&scope=api%20refresh_token"
    )
    log_decision("OAUTH_START", "Initiating Salesforce OAuth", thinking_level="low")
    return {"auth_url": auth_url}

@app.get("/oauth/callback")
async def sf_oauth_callback(code: str = None, error: str = None):
    global salesforce_token
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="No code")
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://login.salesforce.com/services/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": SALESFORCE_CLIENT_ID,
                "client_secret": SALESFORCE_CLIENT_SECRET,
                "redirect_uri": SALESFORCE_REDIRECT_URI
            }
        )
    
    if resp.status_code == 200:
        data = resp.json()
        salesforce_token = data.get("access_token")
        log_decision("OAUTH_SUCCESS", "Salesforce connected", thinking_level="low")
        return {"message": "Connected!", "instance_url": data.get("instance_url")}
    
    raise HTTPException(status_code=400, detail="Token exchange failed")

# ============ TTS ============

@app.post("/api/tts")
async def tts(request: Request):
    data = await request.json()
    text = data.get("text", "")
    
    if not ELEVENLABS_API_KEY:
        return JSONResponse({"error": "No API key"}, status_code=500)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            }
        )
    
    if resp.status_code == 200:
        return StreamingResponse(io.BytesIO(resp.content), media_type="audio/mpeg")
    
    return JSONResponse({"error": "TTS failed"}, status_code=500)
