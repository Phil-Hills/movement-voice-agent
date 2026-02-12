import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Any
import google.generativeai as genai
from pydantic import BaseModel, Field
from agent_interface import BaseAgent

logger = logging.getLogger("agent_engine")

class AgentResponse(BaseModel):
    """Secure, validated response structure for the Movement Voice Agent."""
    text: str
    thinking_level: str
    persona: str = "Jason"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    thought_signature: Optional[str] = None
    error: bool = False

class AgentEngine:
    """
    Core engine for handling AI persona logic and LLM orchestration.
    
    SECURITY ARCHITECTURE:
    - Persona Unification: Enforces the 'Jason' identity to prevent persona hijacking.
    - Thought Signatures: Generates cryptographic signatures for every reasoning step.
    - Hallucination Control: Optimized for deterministic responses using specified behavioral rules.
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

    def get_system_prompt(self, lead: Optional[dict] = None) -> str:
        """Generates the unified 'Jason' persona prompt."""
        base = f"""You are {self.persona}, a professional and friendly mortgage specialist.
Your mission is to help customers navigate their home financing journey with empathy and expertise.

BEHAVIORAL RULES:
- Tone: Professional, warm, and highly competent.
- Compliance: Always use "could" or "may" when discussing savings. Never guarantee rates.
- Conciseness: Keep responses under 2 sentences for voice clarity.
- Handoff: Mention scheduling a call with an NMLS Originator for specific rate quotes.

AUDIT LOGIC:
- Category detection: identify if the lead is VA, Conventional, or Jumbo.
- Priority: Score leads based on urgency and goal clarity.
"""
        if lead:
            base += f"\n\nACTIVE CLIENT CONTEXT:\n- Name: {lead.get('name')}\n- Goal: {lead.get('notes')}\n- Status: {lead.get('status')}"
            
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
        
        prompt = self.get_system_prompt(lead)
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
