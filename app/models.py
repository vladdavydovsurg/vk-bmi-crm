import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
    BigInteger,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ================= LEAD STATUS ENUM =================

class LeadStatus(enum.Enum):
    new = "new"
    in_work = "in_work"
    callback_later = "callback_later"
    no_answer = "no_answer"
    rejected = "rejected"
    consult_scheduled = "consult_scheduled"
    surgery_scheduled = "surgery_scheduled"
    operated = "operated"


# ================= MANAGER =================

class Manager(Base):
    __tablename__ = "managers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    manager_sheet_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # ✅ NEW: group chat id for manager's private supergroup (with you + manager + bot)
    manager_group_chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    leads: Mapped[list["Lead"]] = relationship(
        back_populates="manager"
    )


# ================= LEAD =================

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    telegram_username: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    whatsapp: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    messenger_max: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    weight_kg: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    height_cm: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    bmi: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    lead_type: Mapped[str] = mapped_column(
        String(20),
        default="hot",
        nullable=False,
    )

    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("managers.id"),
        nullable=True,
    )

    manager_status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus),
        default=LeadStatus.new,
        nullable=False,
    )

    comment_from_admin: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    manager: Mapped[Optional["Manager"]] = relationship(
        back_populates="leads"
    )