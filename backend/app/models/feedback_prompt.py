"""Feedback prompt models for trial user check-ins."""

import datetime
import uuid as uuid_mod
from typing import Optional

from beanie import Document
from pydantic import BaseModel, Field


class TriggerRules(BaseModel):
    """Conditions that must all be met for a prompt to fire."""

    min_trial_day: int = 0
    max_trial_day: int = 14
    cooldown_hours: int = 24
    required_milestones: list[str] = []
    forbidden_milestones: list[str] = []


class FeedbackPrompt(Document):
    """Admin-configurable prompt template shown to demo users."""

    uuid: str = Field(default_factory=lambda: uuid_mod.uuid4().hex)
    slug: str  # unique identifier e.g. "welcome_checkin"
    stage: str = "early"  # early | mid | late
    question_text: str
    subject: str  # support ticket subject line
    trigger_rules: TriggerRules = Field(default_factory=TriggerRules)
    enabled: bool = True
    priority: int = 0  # lower = fires first when multiple eligible

    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    class Settings:
        name = "feedback_prompt"
        indexes = ["slug"]


class FeedbackPromptResponse(Document):
    """Per-user state tracking for a single feedback prompt."""

    uuid: str = Field(default_factory=lambda: uuid_mod.uuid4().hex)
    user_id: str
    prompt_slug: str
    status: str = "pending"  # pending | shown | responded | dismissed
    ticket_uuid: Optional[str] = None

    shown_at: Optional[datetime.datetime] = None
    responded_at: Optional[datetime.datetime] = None
    dismissed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    class Settings:
        name = "feedback_prompt_response"
        indexes = [
            [("user_id", 1), ("prompt_slug", 1)],
            [("user_id", 1), ("status", 1)],
            "ticket_uuid",
        ]
