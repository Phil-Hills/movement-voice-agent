import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any
import google.generativeai as genai
from pydantic import BaseModel, Field
from .agent_interface import BaseAgent

logger = logging.getLogger("agent_engine")

class AgentResponse(BaseModel):
    """Secure, validated response structure for the Movement Voice Agent."""
    text: str
    thinking_level: str
    persona: str = "Jason"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    thought_signature: Optional[str] = None
    actions: List[Dict[str, Any]] = []
    error: bool = False

class AgentEngine:
    """
    Core engine for handling AI persona logic and LLM orchestration.
    
    SECURITY ARCHITECTURE:
    - Persona Unification: Enforces the 'Jason' identity to prevent persona hijacking.
    - Thought Signatures: Generates cryptographic signatures for every reasoning step.
    - Hallucination Control: Optimized for deterministic responses using specified behavioral rules.

    STRUCTURED ACTIONS (Orchestration):
You can trigger the following channels by including them in your structured output:
1. `create_task`: {"subject": str, "priority": "High"|"Normal"}
2. `send_sms`: {"message": str} (For instant follow-ups or appointment confirmations)
3. `send_email`: {"subject": str, "body": str} (For program details or formal intros)
4. `send_physical_mail`: {"template": "ThankYouCard"|"ProgramFlyer", "address": str} (For high-value partner nurturing)
5. `handoff`: {"target": "Branch Manager", "reason": str}

Always prioritize the human conversation, then specify necessary multi-channel actions to reinforce the touch-point.
    """
    
    def __init__(self, google_api_key: str, project_id: str):
        self.api_key = google_api_key
        self.project_id = project_id
        self.model_thinking = None
        self.model_flash = None
        self.thought_signatures: Dict[str, Dict] = {}
        
        self._initialize_models()
        self.persona = "Jason"
        
    def _initialize_models(self):
        """Initialize Gemini models with appropriate configurations."""
        if not self.api_key:
            logger.error("No Google API Key provided for AgentEngine")
            return

        genai.configure(api_key=self.api_key)
        
        try:
            self.model_thinking = genai.GenerativeModel(
                model_name='gemini-2.0-flash-thinking-exp',
                generation_config={"thinking_config": {"include_thoughts": True}}
            )
            logger.info("✅ Gemini 2.0 Flash Thinking initialized")
        except Exception as e:
            logger.warning(f"⚠️ Thinking model init failed: {e}")
            
        try:
            self.model_flash = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                tools=[{"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "dynamic"}}}]
            )
            logger.info("✅ Gemini 2.0 Flash initialized")
        except Exception as e:
            logger.warning(f"⚠️ Flash model init failed: {e}")

    def _load_brain_context(self) -> str:
        """Reads the canonical narrative from the brain to inject context."""
        brain_path = "/Users/SoundComputer/.gemini/antigravity/brain/d4541345-fd03-4177-be5e-f302a8a5902f/canonical_narrative.md"
        try:
            if os.path.exists(brain_path):
                with open(brain_path, 'r') as f:
                    return f.read()
        except Exception as e:
            logger.warning(f"⚠️ Could not load brain context: {e}")
        return ""

    def get_system_prompt(self, context: Optional[dict] = None, mode: str = "lead") -> str:
        """Generates the unified 'Jason' persona prompt with mode-specific context."""
        brain_context = self._load_brain_context()
        
        if mode == "partner":
            base = f"""You are {self.persona}, Strategic Relations for our local Mortgage Branch.
Your mission is to reach out to high-performing Real Estate Agents and Brokers to discuss a strategic partnership.

PHASE: Recruitment & Pitching New Programs (VA, Jumbo, High-LTV).

DESIGN AWARENESS (BRAIN):
{brain_context}

BEHAVIORAL RULES:
- Persona: Professional, knowledgeable, and partnership-focused.
- Goal: Briefly mention our "New Specialized Programs" that can help their clients in this current market.
- Call to Action: Schedule a brief introduction call or coffee with our Branch Manager to review the partnership benefits.
- Compliance: Focus on B2B partnership value; do not quote specific consumer interest rates.
"""
        else:
            base = f"""You are {self.persona}, a professional and friendly mortgage specialist.
Your mission is to help customers navigate their home financing journey with empathy and expertise.

DESIGN AWARENESS (BRAIN):
{brain_context}

BEHAVIORAL RULES:
- Tone: Professional, warm, and highly competent.
- Role: You are a "Marathon Agent." You assist the Originator from pre-lead (qualification) to doc collection (chasing missing items) to post-close (retention).
- Compliance (TRID/Reg Z): Always use "could" or "may" when discussing savings. NEVER quote a specific Interest Rate or APR.
- Handoff: Mandatory handoff to a human NMLS Originator for any official rate quotes, APR disclosures, or loan application steps.
- AI Disclosure: Always acknowledge you are an AI if asked or during initial introduction.
"""

        if context:
            base += f"\n\nACTIVE CONTEXT ({mode.upper()}):\n- Name: {context.get('name')}\n- Info: {context.get('notes') or context.get('company', 'N/A')}"
            
        return base

    def generate_thought_signature(self, reasoning: str, previous_sig: Optional[str] = None) -> str:
        """Generates a cryptographic signature for a reasoning step."""
        timestamp = datetime.now().isoformat()
        content = f"{timestamp}:{reasoning}:{previous_sig or 'root'}"
        sig = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"tsig_{sig}"

    async def get_response(self, text: str, lead: Optional[dict] = None, thinking_level: str = "medium") -> dict:
        """Orchestrates LLM response generation with thinking traces and validation."""
        model = self.model_thinking if thinking_level != "minimal" else self.model_flash
        if not model:
            return AgentResponse(
                text="I'm sorry, I'm having trouble connecting to my brain right now.",
                thinking_level=thinking_level,
                error=True
            ).model_dump()
        
        prompt = self.get_system_prompt(lead, mode="partner" if lead.get('type') == 'broker' else "lead")
        history = [{"role": "user", "parts": [prompt]}]
        
        try:
            chat = model.start_chat(history=history)
            response = chat.send_message(text)
            
            # Extract reasoning/thoughts if available (depends on model capabilities/config)
            reasoning = getattr(response, 'candidates', [None])[0].content.parts[0].text if hasattr(response, 'candidates') else ""
            thought_sig = self.generate_thought_signature(reasoning)
            
            res = AgentResponse(
                text=response.text,
                thinking_level=thinking_level,
                persona=self.persona,
                thought_signature=thought_sig
            )
            
            return res.model_dump()
        except Exception as e:
            logger.error(f"Error in AgentEngine: {e}")
            return AgentResponse(
                text="I encountered an error processing your request.",
                thinking_level=thinking_level,
                error=True
            ).model_dump()
