import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pathwise_db.base import Base

__all__ = ["Profile", "ProfileEducation", "ProfileExperience", "ProfilePlan", "ResumeParseUsage"]

YEAR_MONTH = "'^[0-9]{4}-(0[1-9]|1[0-2])$'"


class ProfilePlan(enum.Enum):
    guest = "guest"
    pro = "pro"


def _month_range_checks() -> tuple[CheckConstraint, ...]:
    return (
        CheckConstraint(f"start_month IS NULL OR start_month ~ {YEAR_MONTH}", name="start_month_format"),
        CheckConstraint(f"end_month IS NULL OR end_month ~ {YEAR_MONTH}", name="end_month_format"),
    )


class Profile(Base):
    """One row per Cognito user (user_id = the token's `sub`). Name and email come from the resume."""

    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    profile_code: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        unique=True,
        server_default=text("upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8))"),
    )
    plan: Mapped[ProfilePlan] = mapped_column(
        Enum(ProfilePlan, name="profile_plan"), nullable=False, server_default=ProfilePlan.guest.value
    )
    full_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    current_designation: Mapped[str | None] = mapped_column(String(200))
    current_location: Mapped[str | None] = mapped_column(String(200))
    preferred_locations: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)), nullable=False, server_default=text("'{}'")
    )
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(100)), nullable=False, server_default=text("'{}'"))
    resume_key: Mapped[str | None] = mapped_column(String(300))
    resume_file_name: Mapped[str | None] = mapped_column(String(255))
    resume_size_bytes: Mapped[int | None] = mapped_column(Integer)
    resume_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    experiences: Mapped[list["ProfileExperience"]] = relationship(order_by="ProfileExperience.position")
    educations: Mapped[list["ProfileEducation"]] = relationship(order_by="ProfileEducation.position")


class ProfileExperience(Base):
    __tablename__ = "profile_experiences"
    __table_args__ = (
        *_month_range_checks(),
        Index("ix_profile_experiences_user_id_position", "user_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    designation: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_month: Mapped[str | None] = mapped_column(String(7))
    end_month: Mapped[str | None] = mapped_column(String(7))
    description: Mapped[str | None] = mapped_column(Text)


class ProfileEducation(Base):
    __tablename__ = "profile_educations"
    __table_args__ = (
        *_month_range_checks(),
        Index("ix_profile_educations_user_id_position", "user_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(200))
    start_month: Mapped[str | None] = mapped_column(String(7))
    end_month: Mapped[str | None] = mapped_column(String(7))


class ResumeParseUsage(Base):
    """Resume parses per user per day (UTC), so one account can't run up AI costs."""

    __tablename__ = "resume_parse_usage"

    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("profiles.user_id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
