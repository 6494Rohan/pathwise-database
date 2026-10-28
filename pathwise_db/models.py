import enum
import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pathwise_db.base import Base
from pathwise_db.profiles import Profile, ProfileEducation, ProfileExperience, ProfilePlan, ResumeParseUsage

__all__ = [
    "Base",
    "Company",
    "EmploymentType",
    "Job",
    "JobStatus",
    "Profile",
    "ProfileEducation",
    "ProfileExperience",
    "ProfilePlan",
    "ResumeParseUsage",
    "Skill",
    "WorkMode",
    "job_skills",
]


class EmploymentType(enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    internship = "internship"
    contract = "contract"


class WorkMode(enum.Enum):
    on_site = "on_site"
    remote = "remote"
    hybrid = "hybrid"


class JobStatus(enum.Enum):
    open = "open"
    closed = "closed"


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


job_skills = Table(
    "job_skills",
    Base.metadata,
    Column("job_id", UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_job_skills_skill_id", "skill_id"),
)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_verified: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = _created_at()

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("min_experience_years >= 0", name="min_experience_non_negative"),
        CheckConstraint(
            "max_experience_years IS NULL OR max_experience_years >= min_experience_years",
            name="experience_range",
        ),
        CheckConstraint(
            "salary_min_lpa IS NULL OR salary_max_lpa IS NULL OR salary_max_lpa >= salary_min_lpa",
            name="salary_range",
        ),
        Index("ix_jobs_location", "location", postgresql_using="gist"),
        Index("ix_jobs_posted_at", "posted_at"),
        Index("ix_jobs_company_id", "company_id"),
        Index("ix_jobs_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type"), nullable=False
    )
    work_mode: Mapped[WorkMode] = mapped_column(Enum(WorkMode, name="work_mode"), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    # The GiST index is declared in __table_args__ so it follows the naming convention and isn't created twice.
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    min_experience_years: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    max_experience_years: Mapped[int | None] = mapped_column(SmallInteger)
    salary_min_lpa: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    salary_max_lpa: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), nullable=False, server_default=JobStatus.open.value
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = _created_at()

    company: Mapped[Company] = relationship(back_populates="jobs")
    skills: Mapped[list[Skill]] = relationship(secondary=job_skills)
