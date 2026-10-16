"""Tables from docs/DATA_MODEL.md section 2. Enum-like columns are short strings checked by the services."""
from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime

UNIT_ID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def new_unit_id() -> str:
    """Opaque platform ID, random, never derived from a bag number (deck: unit IDs not linkable to donors)."""
    return "U-" + "".join(secrets.choice(UNIT_ID_ALPHABET) for _ in range(8))


class Centre(Base):
    __tablename__ = "centre"
    id: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(12))                 # hospital | collection
    area: Mapped[str] = mapped_column(String(60))
    public_phone: Mapped[str] = mapped_column(String(40))
    mock_sender: Mapped[str | None] = mapped_column(String(40), nullable=True)   # fictional mock-channel number
    daily_demand_mean: Mapped[float] = mapped_column(Float)       # simulated parameter (d_bar)
    group_demand_shares: Mapped[list] = mapped_column(JSON)      # w_g, 8 floats
    last_post_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    """Demo user (ADR-004). NOT real authentication."""
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20))                 # coordinator | centre_staff | medical_officer
    centre_id: Mapped[str | None] = mapped_column(ForeignKey("centre.id"), nullable=True)


class StockPost(Base):
    __tablename__ = "stock_post"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    centre_id: Mapped[str] = mapped_column(ForeignKey("centre.id"))
    posted_at: Mapped[datetime] = mapped_column(UTCDateTime)
    posted_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(16))               # form | csv | mock_channel | seed
    parse_draft_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_count: Mapped[int] = mapped_column(Integer)


class Unit(Base):
    __tablename__ = "unit"
    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=new_unit_id)
    centre_id: Mapped[str] = mapped_column(ForeignKey("centre.id"))
    stock_post_id: Mapped[int | None] = mapped_column(ForeignKey("stock_post.id"), nullable=True)
    component: Mapped[str] = mapped_column(String(3))             # RDP | SDP
    abo_rh: Mapped[str] = mapped_column(String(3))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    received_via_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(12), default="listed")
    # listed | reserved | in_transit | superseded | not_found
    __table_args__ = (Index("ix_unit_centre_status_group", "centre_id", "status", "abo_rh", "expires_at"),
                      Index("ix_unit_status_group", "status", "abo_rh"))


class Shortfall(Base):
    __tablename__ = "shortfall"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    centre_id: Mapped[str] = mapped_column(ForeignKey("centre.id"))
    abo_rh: Mapped[str] = mapped_column(String(3))
    component: Mapped[str] = mapped_column(String(3))
    identical_only: Mapped[bool] = mapped_column(Boolean, default=False)
    count_requested: Mapped[int] = mapped_column(Integer)
    count_open: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(8), default="open")   # open | covered | closed
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    __table_args__ = (Index("ix_shortfall_status_centre", "status", "centre_id"),)


class TrustCounter(Base):
    __tablename__ = "trust_counter"
    centre_id: Mapped[str] = mapped_column(ForeignKey("centre.id"), primary_key=True)
    bucket: Mapped[int] = mapped_column(Integer, primary_key=True)
    alpha: Mapped[float] = mapped_column(Float)
    beta: Mapped[float] = mapped_column(Float)
    seeded_alpha: Mapped[float] = mapped_column(Float, default=0.0)
    seeded_beta: Mapped[float] = mapped_column(Float, default=0.0)
    n_confirmations: Mapped[int] = mapped_column(Integer, default=0)


class TransportEstimate(Base):
    """ASSUMPTION: seeded courier minutes per pair (default 90, the simulator's base assumption)."""
    __tablename__ = "transport_estimate"
    from_centre: Mapped[str] = mapped_column(ForeignKey("centre.id"), primary_key=True)
    to_centre: Mapped[str] = mapped_column(ForeignKey("centre.id"), primary_key=True)
    minutes: Mapped[float] = mapped_column(Float)


class MatchRun(Base):
    __tablename__ = "match_run"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_at: Mapped[datetime] = mapped_column(UTCDateTime)
    run_by: Mapped[str] = mapped_column(ForeignKey("user.id"))
    policy: Mapped[str] = mapped_column(String(10))
    acknowledged_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    inputs_digest: Mapped[str] = mapped_column(String(64))
    n_suggested: Mapped[int] = mapped_column(Integer)
    notes: Mapped[list] = mapped_column(JSON, default=list)


class Transfer(Base):
    __tablename__ = "transfer"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_run_id: Mapped[int] = mapped_column(ForeignKey("match_run.id"))
    shortfall_id: Mapped[int] = mapped_column(ForeignKey("shortfall.id"))
    from_centre: Mapped[str] = mapped_column(ForeignKey("centre.id"))
    to_centre: Mapped[str] = mapped_column(ForeignKey("centre.id"))
    component: Mapped[str] = mapped_column(String(3))
    abo_rh_needed: Mapped[str] = mapped_column(String(3))
    abo_rh_offered: Mapped[str] = mapped_column(String(3))
    tier: Mapped[int] = mapped_column(Integer)
    policy: Mapped[str] = mapped_column(String(10))
    anti_d_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    qty_requested: Mapped[int] = mapped_column(Integer)
    qty_confirmed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listing_bucket: Mapped[int] = mapped_column(Integer)
    transport_min: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="suggested")
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    box_validated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)   # recorded, not verified (D-09)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    units: Mapped[list["TransferUnit"]] = relationship(cascade="all, delete-orphan")
    __table_args__ = (Index("ix_transfer_status", "status"), Index("ix_transfer_from", "from_centre", "status"),
                      Index("ix_transfer_to", "to_centre", "status"))


class TransferUnit(Base):
    __tablename__ = "transfer_unit"
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfer.id"), primary_key=True)
    unit_id: Mapped[str] = mapped_column(ForeignKey("unit.id"), primary_key=True)


class AuditEvent(Base):
    """Append-only: no route updates or deletes audit rows."""
    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    actor_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(20))
    entity: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(20))
    from_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (Index("ix_audit_entity", "entity", "entity_id", "at"),)


class InboundMessage(Base):
    """Mock channel only (ADR-002). Stage 4."""
    __tablename__ = "inbound_message"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime)
    channel: Mapped[str] = mapped_column(String(16))              # mock_whatsapp | mock_sms | paste
    sender: Mapped[str] = mapped_column(String(40))
    centre_id: Mapped[str | None] = mapped_column(ForeignKey("centre.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text)


class ParseDraft(Base):
    """Stage 4."""
    __tablename__ = "parse_draft"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inbound_message_id: Mapped[int] = mapped_column(ForeignKey("inbound_message.id"))
    parser: Mapped[str] = mapped_column(String(8))
    model: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    needs_review_reasons: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    __table_args__ = (Index("ix_parse_draft_status", "status"),)


class Meta(Base):
    """Key/value settings stored with the demo DB (e.g. the demo clock anchor)."""
    __tablename__ = "meta"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
