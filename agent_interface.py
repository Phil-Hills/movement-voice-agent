"""
Q Protocol Agent Interface.

This module defines the standard interface for AI Agents within the
Q Protocol system. It handles structured communication, task requests,
and verifiable receipts (TaskResponse).
"""

import datetime
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("agent_interface")

@dataclass
class AgentCard:
    """
    Metadata card describing an agent's identity and capabilities.
    """
    uuid: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)

@dataclass
class TaskRequest:
    """
    A structured request for an agent to perform work.
    """
    requester_id: str
    content: str
    task_id: str = field(default_factory=lambda: str(datetime.datetime.now().timestamp()))
    context: Dict = field(default_factory=dict)
    headers: Dict = field(default_factory=lambda: {
        "x-a2a-context-id": str(uuid.uuid4()),
        "x-a2a-hop-count": "0",
        "x-a2a-timestamp": datetime.datetime.utcnow().isoformat()
    })

@dataclass
class TaskResponse:
    """
    A verifiable receipt of work performed by an agent.
    """
    task_id: str
    responder_id: str
    status: str
    output: str
    artifacts: List = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    headers: Dict = field(default_factory=dict)
    
    def to_receipt(self) -> str:
        """
        Generate a concise Q Protocol Receipt String.

        Returns:
            str: The formatted receipt (RCPT:Responder:ID:Status:Size).
        """
        return f"RCPT:{self.responder_id}:{self.task_id}:{self.status}:{len(self.output)}b"

class BaseAgent:
    """
    Abstract base agent that communicates via the A2A+Cube protocol.

    Ported for Movement Voice Agent.
    """
    def __init__(self, name: str, description: str, capabilities: Optional[List[str]] = None):
        """
        Initialize the agent with a card and stats.

        Args:
            name: Agent name.
            description: Description of role.
            capabilities: List of capability strings.
        """
        self.card = AgentCard(
            uuid=str(uuid.uuid4()),
            name=name,
            description=description,
            capabilities=capabilities or []
        )
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "tasks_completed": 0
        }
        logger.info(f"Agent {name} initialized ({self.card.uuid})")

    def sign_off_task(self, request: TaskRequest, status: str, output: str) -> TaskResponse:
        """
        Generate a Receipt (TaskResponse) for a completed task.

        This constitutes the 'Sign-off' procedure required by Q Protocol.

        Args:
            request: The original TaskRequest.
            status: Outcome status (e.g., 'success').
            output: Resulting content/summary.

        Returns:
            TaskResponse: The signed receipt.
        """
        response = TaskResponse(
            task_id=request.task_id,
            responder_id=self.card.name,
            status=status,
            output=output,
            headers=request.headers
        )
        self.stats["tasks_completed"] += 1
        return response

    def create_ad_hoc_receipt(self, action: str, details: str, status: str = "completed") -> TaskResponse:
        """
        Create a receipt for an internal action without a formal request.

        Useful for logging autonomous decisions (e.g., Company Research).

        Args:
            action: The action name.
            details: Details of the action.
            status: Outcome status.

        Returns:
            TaskResponse: The generated receipt.
        """
        response = TaskResponse(
            task_id=f"adhoc_{datetime.datetime.now().timestamp()}",
            responder_id=self.card.name,
            status=status,
            output=f"ACTION:{action} DETAILS:{details}",
            headers={"x-a2a-type": "ADHOC_RECEIPT"}
        )
        self.stats["tasks_completed"] += 1
        return response
