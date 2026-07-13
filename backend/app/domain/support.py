from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConversationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: int = Field(ge=1)
    role: Literal["customer", "agent"]
    timestamp: datetime
    text: str = Field(min_length=2)
    sentiment: float = Field(ge=-1, le=1)


class SupportConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(pattern=r"^SUP-[A-Z0-9-]+$")
    customer_id: str = Field(pattern=r"^SYN-CUST-[0-9]+$")
    started_at: datetime
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    industry: Literal["telecom", "ecommerce", "banking", "saas"]
    channel: Literal["chat", "email", "voice-transcript"]
    issue_type: str = Field(min_length=2)
    sentiment_arc: Literal["recovery", "steady-positive", "escalation"]
    resolution_status: Literal["resolved", "escalated"]
    turns: list[ConversationTurn] = Field(min_length=4, max_length=10)
    synthetic: bool = True
    disclaimer: str = "Synthetic customer-support conversation. Not a real customer interaction."

    @model_validator(mode="after")
    def validate_turn_order(self) -> "SupportConversation":
        if self.turns[0].role != "customer":
            raise ValueError("conversation must start with a customer turn")
        if any(left.role == right.role for left, right in zip(self.turns, self.turns[1:])):
            raise ValueError("conversation roles must alternate")
        if [turn.turn_id for turn in self.turns] != list(range(1, len(self.turns) + 1)):
            raise ValueError("conversation turn IDs must be sequential")
        if any(turn.timestamp < self.started_at for turn in self.turns):
            raise ValueError("conversation turns cannot precede the conversation start")
        if any(left.timestamp >= right.timestamp for left, right in zip(self.turns, self.turns[1:])):
            raise ValueError("conversation turn timestamps must increase")
        return self
