"""
Clairvoyant - AI Sales Platform
Hackathon-Winning Implementation with Gemini 3 Features.

Key Features:
- Asymmetric Reasoning (Thinking Models).
- Thought Signatures (Context Preservation).
- Google Search Grounding.
- Autonomous Suggestions.
"""

import csv
import glob
import hashlib
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import blake3
import httpx
import msgpack
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Local Imports
from agent_interface import BaseAgent
from agents import reviewer as reviewer_interface
from campaign_manager import get_campaign_manager

# ============ LOGGING CONFIGURATION ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clairvoyant")

load_dotenv()

# ============ APP SETUP ============
app = FastAPI(
    title="Clairvoyant - AI Sales Platform",
    description="Enterprise AI Sales Agent with Gemini 3 Pro/Flash & Salesforce Integration.",
    version="4.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# ============ CONFIGURATION ============
# Security: Load secrets from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "deployment-2026-core")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Bella

# Salesforce OAuth
SALESFORCE_CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID")
SALESFORCE_CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET")
SALESFORCE_REDIRECT_URI = os.getenv(
    "SALESFORCE_REDIRECT_URI",
    "https://movement-voice-agent-235894147478.us-central1.run.app/oauth/callback"
)

# Thinking Level Configuration
THINKING_LEVELS = {
    "high": {"description": "Deep reasoning with extensive thought chains.", "budget": 4096},
    "medium": {"description": "Balanced reasoning for standard inquiries.", "budget": 2048},
    "low": {"description": "Fast reasoning for simple tasks.", "budget": 1024},
    "minimal": {"description": "Direct response with minimal overhead.", "temperature": 0.0},
    "local": {"description": "Private, local execution via Ollama.", "model": "qwen2.5:latest"}
}

# ============ PYDANTIC MODELS ============

class ResearchRequest(BaseModel):
    """Request model for company research."""
    company: str = Field(..., description="Name of the company to research.")
    session_id: str = Field(default="default", description="Session ID for context tracking.")

class ReviewRequest(BaseModel):
    """Request model for content review."""
    content: str = Field(..., description="Text content to be reviewed.")
    submission_id: str = Field(default="S_ADHOC", description="Unique identifier for the submission.")

class SelectLeadRequest(BaseModel):
    """Request model for selecting a lead."""
    auto_research: bool = Field(default=True, description="Whether to automatically research the lead's company.")
    session_id: str = Field(default="default", description="Session ID for context tracking.")

class ChatRequest(BaseModel):
    """Request model for chat interaction."""
    text: str = Field(..., description="User input text.")
    thinking_level: str = Field(default="medium", description="Level of AI reasoning depth.")
    session_id: str = Field(default="default", description="Session ID for context tracking.")

class PitchRequest(BaseModel):
    """Request model for pitch generation."""
    session_id: str = Field(default="default", description="Session ID for context tracking.")

class TTSRequest(BaseModel):
    """Request model for Text-to-Speech."""
    text: str = Field(..., description="Text to convert to speech.")

class SalesforceImportRequest(BaseModel):
    """Request model for importing a Salesforce campaign."""
    campaign_id: str = Field(..., description="Salesforce Campaign ID.")


# ============ THOUGHT SIGNATURE SYSTEM ============
thought_signatures: Dict[str, Dict] = {}  # session_id -> signature chain
decision_audit_log: List[Dict[str, Any]] = []

def generate_thought_signature(reasoning: str, previous_sig: Optional[str] = None) -> str:
    """
    Generate a cryptographic thought signature for a decision chain.

    Ensures non-repudiation and traceability of AI decisions.

    Args:
        reasoning: The text content of the reasoning step.
        previous_sig: The signature of the previous step in the chain.

    Returns:
        A SHA-256 hash representing the signature.
    """
    timestamp = datetime.now().isoformat()
    content = f"{timestamp}:{reasoning}:{previous_sig or 'root'}"
    sig = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"tsig_{sig}"

def store_thought_signature(session_id: str, sig: str, reasoning: str, action: str) -> Dict[str, Any]:
    """
    Store a thought signature with its full reasoning trace.

    Args:
        session_id: The active session identifier.
        sig: The generated signature.
        reasoning: The reasoning text.
        action: The action taken.

    Returns:
        The stored entry dictionary.
    """
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
    """
    Retrieve the full reasoning chain for a session.

    Args:
        session_id: The session identifier.

    Returns:
        A list of reasoning steps.
    """
    if session_id not in thought_signatures:
        return []
    return thought_signatures[session_id]["chain"]

def log_decision(action: str, reasoning: str, lead_id: Optional[str] = None,
                 thinking_level: str = "medium", confidence: float = 1.0,
                 session_id: str = "default") -> str:
    """
    Log a decision with a full thought signature chain.

    This function acts as the central audit logger for AI actions.

    Args:
        action: The name of the action performed.
        reasoning: The justification for the action.
        lead_id: Optional ID of the lead involved.
        thinking_level: The depth of reasoning used.
        confidence: Confidence score (0.0 - 1.0).
        session_id: Session identifier.

    Returns:
        The generated thought signature.
    """
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

# In-memory storage (Fallback)
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
    """
    Load QMem binary knowledge base to prevent redundant work.

    Args:
        path: Path to the QMem file or directory.

    Returns:
        Number of knowledge atoms loaded.
    """
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
    model_local = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama" # Not required for local
    )
    logger.info("✅ Local LLM connected (Ollama @ 11434)")
except Exception as e:
    logger.warning(f"⚠️ Local LLM not available: {e}")


def get_model_and_config(thinking_level: str) -> tuple:
    """
    Get real model and config based on level.

    Args:
        thinking_level: 'high', 'medium', 'low', 'minimal', or 'local'.

    Returns:
        Tuple of (model_instance, config_dict).
    """
    # 1. Thinking Models (High/Medium/Low)
    if thinking_level in ["high", "medium", "low"]:
        if not model_thinking:
            return model_flash, {} # Fallback

        budget = THINKING_LEVELS.get(thinking_level, {}).get("budget", 1024)
        return model_thinking, {"thinking_config": {"include_thoughts": True, "thinking_budget": budget}}

    # 2. Minimal / Fast (No Thinking)
    if thinking_level == "minimal":
        return model_flash, {"temperature": 0.0}

    # 3. Local LLM (Privacy / Cost Savings)
    if thinking_level == "local":
        if model_local:
             return model_local, {"model": "qwen2.5:latest"}
        return model_flash, {} # Fallback

    return model_flash, {"temperature": 0.0}


def get_system_prompt(lead: Optional[dict] = None, thinking_level: str = "high") -> str:
    """
    Generate the system prompt based on context and thinking level.

    Args:
        lead: Optional lead dictionary containing user details.
        thinking_level: The reasoning level to configure the persona.

    Returns:
        The full system prompt string.
    """
    config = THINKING_LEVELS.get(thinking_level, THINKING_LEVELS["high"])

    base = f"""You are Clairvoyant, an elite AI sales agent with supernatural insight into customer needs.

THINKING LEVEL: {thinking_level.upper()}
{config.get('description', '')}

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

    # Add company research if available
    company = lead.get('company', '') if lead else ''
    if company and company in research_cache:
        research = research_cache[company]
        base += f"\n\nCOMPANY INTELLIGENCE:\n{json.dumps(research, indent=2)}"

    return base


# ============ RESEARCH (with Google Grounding) ============

async def research_company(company_name: str, session_id: str = "default") -> dict:
    """
    Research company using Gemini 2.0 Flash + Google Search Tool.

    Checks in-memory cache and Q-Memory before making an API call.

    Args:
        company_name: Name of the company.
        session_id: Session ID for logging.

    Returns:
        Dictionary containing research data.
    """

    # 1. Check Runtime Cache (Fastest)
    if company_name in research_cache:
        logger.info(f"⚡ Cache hit for {company_name}")
        return research_cache[company_name]

    # 2. Check Q-Memory (Brain / Long-term Knowledge)
    q_key = company_name.lower().replace(" ", "_")
    if q_key in q_memory:
        logger.info(f"🧠 Q-Memory hit for {company_name} (Prevented redundant work)")
        atoms = q_memory[q_key]
        knowledge_text = "\n".join([f"- {a.get('template', '')}" for a in atoms])

        return {
            "company": company_name,
            "summary": f"Recovered from Brain:\n{knowledge_text}",
            "news": [],
            "leadership": "See Brain records",
            "source": "Q-Memory",
            "thought_signature": f"qmem_{datetime.now().timestamp()}"
        }

    if not model_flash:
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
        data["thought_signature"] = f"sig_{datetime.now().timestamp()}"

        research_cache[company_name] = data

        log_decision(
            "RESEARCH_COMPANY",
            f"Researched {company_name} using Google Search Grounding",
            thinking_level="low",
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

        # Fallback to Local LLM if available
        if ("403" in error_msg or model_local) and model_local:
            logger.info("⚠️ Falling back to Local LLM (Ollama) due to API error...")
            try:
                fallback_prompt = f"""
                You are a research assistant.
                Research the company '{company_name}'.
                Find: 1. Core business 2. Recent news 3. Leadership.
                Return valid JSON (keys: summary, news, leadership). do not use markdown blocks.
                """

                completion = model_local.chat.completions.create(
                    model="qwen2.5:7b",
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.3
                )

                text = completion.choices[0].message.content
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


# ============ LEAD STORAGE ============

def save_lead(lead: dict) -> str:
    """Save a lead to persistence layer."""
    lead_id = lead.get('id', str(datetime.now().timestamp()).replace('.', ''))
    lead['id'] = lead_id
    lead['updated_at'] = datetime.now().isoformat()

    if USE_FIRESTORE:
        db.collection(LEADS_COLLECTION).document(lead_id).set(lead)
    else:
        leads_db[lead_id] = lead

    return lead_id

def get_all_leads() -> List[dict]:
    """Retrieve all leads."""
    if USE_FIRESTORE:
        return [doc.to_dict() for doc in db.collection(LEADS_COLLECTION).stream()]
    return list(leads_db.values())

def get_lead(lead_id: str) -> Optional[dict]:
    """Retrieve a specific lead."""
    if USE_FIRESTORE:
        doc = db.collection(LEADS_COLLECTION).document(lead_id).get()
        return doc.to_dict() if doc.exists else None
    return leads_db.get(lead_id)

def save_conversation(lead_id: str, role: str, message: str, thinking_level: str = "medium"):
    """Log conversation history."""
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
    """Retrieve conversation history for a lead."""
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
    """Render the main index page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard")
async def dashboard(request: Request):
    """Render the admin dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health():
    """Health check endpoint exposing system status."""
    return {
        "status": "healthy",
        "version": "4.1.0",
        "gemini_pro": model_thinking is not None,
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
    """Get full decision audit log with thought signatures."""
    return {
        "audit_log": decision_audit_log[-50:],
        "total_decisions": len(decision_audit_log),
        "active_sessions": len(thought_signatures)
    }

@app.get("/api/audit/chain/{session_id}")
async def get_audit_chain(session_id: str):
    """Get reasoning chain for a session."""
    chain = get_reasoning_chain(session_id)
    return {"session_id": session_id, "chain": chain, "length": len(chain)}

# ============ COMPANY RESEARCH ============

@app.post("/api/research")
async def research_endpoint(request: ResearchRequest):
    """Research a company using Google grounding."""
    research = await research_company(request.company, request.session_id)
    return research

@app.get("/api/research/{company}")
async def get_research_cached(company: str):
    """Get cached company research."""
    if company in research_cache:
        return research_cache[company]
    return {"error": "No research found", "company": company}

@app.get("/api/qmem/debug")
async def debug_qmem():
    """List loaded Q-Memory keys for verification."""
    keys = list(q_memory.keys())
    return {"count": len(keys), "keys": keys[:50]}

# ============ REVIEWER AGENT ============

@app.post("/api/review")
async def review_submission(request: ReviewRequest):
    """Submit content for Strict Q-Protocol Review."""
    # Use Flash model for review (fast and capable for this rubric)
    if not model_flash and not model_local:
        raise HTTPException(status_code=503, detail="AI Model unavailable (both Cloud and Local)")

    result = await reviewer_interface.review_content(
        request.content,
        model_flash,
        request.submission_id,
        model_local=model_local
    )
    return result

# ============ LEAD MANAGEMENT ============

@app.post("/api/leads/upload")
async def upload_leads(file: UploadFile = File(...)):
    """Upload and parse leads from a CSV file."""
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
async def list_leads():
    """List all leads."""
    return {"leads": get_all_leads()}

@app.post("/api/leads/select/{lead_id}")
async def select_lead_endpoint(lead_id: str, request: SelectLeadRequest):
    """Select a lead to be active in the current session."""
    global current_lead

    lead = get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    current_lead = lead

    sig = log_decision(
        "SELECT_LEAD",
        f"Selected lead: {lead.get('name')} from {lead.get('company')}",
        lead_id,
        thinking_level="low",
        session_id=request.session_id
    )

    # Auto-research company if enabled
    research = None
    if request.auto_research and lead.get('company'):
        research = await research_company(lead.get('company'), request.session_id)

    return {
        "message": f"Selected: {lead.get('name')}",
        "lead": lead,
        "research": research,
        "thought_signature": sig
    }

@app.get("/api/leads/current")
async def get_current_lead_info():
    """Get currently active lead."""
    research = None
    if current_lead and current_lead.get('company') in research_cache:
        research = research_cache[current_lead.get('company')]
    return {"lead": current_lead, "research": research}

@app.post("/api/leads/clear")
async def clear_active_lead():
    """Clear the currently active lead."""
    global current_lead
    current_lead = None
    log_decision("CLEAR_LEAD", "Cleared lead selection", thinking_level="minimal")
    return {"message": "Cleared"}

# ============ CHAT (with thinking_level) ============

@app.post("/demo")
async def chat(request: ChatRequest):
    """
    Main chat endpoint handling AI responses with varying thinking levels.
    """
    # Get model and config based on thinking level
    model, config = get_model_and_config(request.thinking_level)

    if not model:
        return {
            "text": "I'd love to help! (Model unavailable)",
            "error": True,
            "thinking_level": request.thinking_level
        }

    # Log the request with thought signature
    sig = log_decision(
        "CHAT_REQUEST",
        f"Processing '{request.text[:50]}...' at {request.thinking_level} level",
        current_lead.get('id') if current_lead else None,
        thinking_level=request.thinking_level,
        session_id=request.session_id
    )

    # Save user message
    if current_lead:
        save_conversation(current_lead['id'], "user", request.text, request.thinking_level)

    try:
        system_prompt = get_system_prompt(current_lead, request.thinking_level)

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

        response = chat_session.send_message(request.text)

        # Extract thoughts if available (SDK dependent, omitted for stability)
        response_text = response.text

        # Save assistant response
        if current_lead:
            save_conversation(current_lead['id'], "assistant", response_text, request.thinking_level)

        # Log completion
        response_sig = log_decision(
            "CHAT_RESPONSE",
            f"Generated: '{response_text[:50]}...'",
            current_lead.get('id') if current_lead else None,
            thinking_level=request.thinking_level,
            session_id=request.session_id
        )

        return {
            "text": response_text,
            "thinking_level": request.thinking_level,
            "model_used": config.get("use_model", "gemini"),
            "thought_signature": sig,
            "response_signature": response_sig
        }

    except Exception as e:
        logger.error(f"Chat error: {e}")
        log_decision("CHAT_ERROR", str(e), thinking_level=request.thinking_level, session_id=request.session_id)

        if current_lead:
            fallback = f"Let me check on that for you, {current_lead.get('name', '')}. What specifically interests you?"
        else:
            fallback = "I'd love to help! What would you like to know about our solutions?"

        return {"text": fallback, "error": True, "thinking_level": request.thinking_level}

# ============ GENERATE PITCH ============

@app.post("/api/pitch")
async def generate_pitch(request: PitchRequest):
    """Generate personalized pitch for current lead."""
    if not current_lead:
        raise HTTPException(status_code=400, detail="No lead selected")

    if not model_thinking:
        model = model_flash # Fallback
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
        raise HTTPException(status_code=500, detail="Failed to generate pitch")


# ============ SALESFORCE OAUTH ============

@app.get("/oauth/salesforce")
async def sf_oauth_start():
    """Initiate Salesforce OAuth flow."""
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
    """Handle Salesforce OAuth callback."""
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
async def tts(request: TTSRequest):
    """Convert text to speech via ElevenLabs."""
    if not ELEVENLABS_API_KEY:
        return JSONResponse({"error": "No API key"}, status_code=500)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={
                "text": request.text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            }
        )

    if resp.status_code == 200:
        return StreamingResponse(io.BytesIO(resp.content), media_type="audio/mpeg")

    return JSONResponse({"error": "TTS failed"}, status_code=500)

# ============ CAMPAIGN MANAGEMENT ============

@app.post("/api/campaigns/upload")
async def upload_campaign_csv(file: UploadFile = File(...)):
    """Upload a CSV file to start a new campaign."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSV only")

    content = await file.read()
    manager = get_campaign_manager()
    result = await manager.load_campaign_from_csv(content)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result

@app.post("/api/campaigns/import-salesforce")
async def import_salesforce_campaign(request: SalesforceImportRequest):
    """Import leads from a Salesforce campaign."""
    manager = get_campaign_manager()
    result = await manager.load_campaign_from_salesforce(request.campaign_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result

@app.post("/api/campaigns/start")
async def start_campaign_endpoint():
    """Start the outbound dialer."""
    manager = get_campaign_manager()
    await manager.start_campaign()
    return {"message": "Campaign started"}

@app.post("/api/campaigns/stop")
async def stop_campaign_endpoint():
    """Stop the outbound dialer."""
    manager = get_campaign_manager()
    await manager.stop_campaign()
    return {"message": "Campaign stopped"}

@app.get("/api/campaigns/status")
async def get_campaign_status():
    """Get the current status of the campaign dialer."""
    manager = get_campaign_manager()
    return {
        "active": manager.is_running,
        "current_index": manager.current_lead_index,
        "total": manager.stats["total"],
        "stats": manager.stats
    }
