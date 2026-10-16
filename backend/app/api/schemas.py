"""Request bodies. extra="forbid" everywhere: an unexpected field (e.g. a patient name) is a 400 (FR-L4)."""
from __future__ import annotations

from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UnitIn(Strict):
    component: str = "RDP"
    abo_rh: str
    expires_at: datetime | None = None
    expires_on: date | None = Field(default=None, description="local date; unit usable through the end of it")

    @model_validator(mode="after")
    def one_expiry(self):
        if (self.expires_at is None) == (self.expires_on is None):
            raise ValueError("give exactly one of expires_at or expires_on")
        return self


class StockPostIn(Strict):
    units: list[UnitIn]


class ShortfallIn(Strict):
    abo_rh: str
    component: str = "RDP"
    count: int = Field(ge=1, le=50)
    identical_only: bool = False


class MatchRunIn(Strict):
    policy: str = "strict"
    acknowledged_by: str | None = None


class ConfirmIn(Strict):
    units_available: int = Field(ge=0)
    note: str = ""


class NoteIn(Strict):
    note: str = ""


class ReasonIn(Strict):
    reason: str = Field(min_length=1)


class DispatchIn(Strict):
    box_validated: bool = False
    transport_min: float | None = Field(default=None, gt=0, le=24 * 60)


class InboundIn(Strict):
    """Mock channel only. Not the WhatsApp Cloud API webhook format (ADR-002)."""
    channel: Literal["mock_whatsapp", "mock_sms", "paste"] = "paste"
    text: str = Field(min_length=1, max_length=2000)
    sender: str | None = None
    centre_id: str | None = None


class ParseIn(Strict):
    text: str = Field(min_length=1, max_length=2000)
    centre_id: str | None = None
    mode: Literal["rules", "llm", "auto"] | None = None


class DraftItemIn(Strict):
    abo_rh: str | None = None
    component: Literal["RDP", "SDP"] | None = None
    count: int | None = Field(default=None, ge=0, le=50)
    expiry_date: date | None = None
    source_span: str = ""


class DraftEditIn(Strict):
    message_type: Literal["stock_post", "shortfall", "other"] | None = None
    items: list[DraftItemIn] | None = None
    commit_mode: Literal["add", "replace"] | None = None
    patient_data_redacted: bool = False
