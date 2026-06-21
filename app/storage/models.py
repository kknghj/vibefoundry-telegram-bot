from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship

from app.utils.time import utcnow


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    type = Column(String(20), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    last_checked_at = Column(DateTime(timezone=True))
    last_success_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    config_json = Column(Text)


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (UniqueConstraint("source_name", "external_id", name="uq_candidate_source_external"),)

    id = Column(Integer, primary_key=True)
    source_name = Column(String(80), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    author = Column(String(255))
    project_name = Column(String(255), index=True)
    service_name = Column(String(255), index=True)
    raw_text = Column(Text)
    language = Column(String(20))
    published_at = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    engagement_json = Column(Text)
    category = Column(String(80), index=True)
    priority_type = Column(String(80))
    summary_ko = Column(Text)
    translation_ko = Column(Text)
    implementation_notes_ko = Column(Text)
    problem_solved_ko = Column(Text)
    reaction_ko = Column(Text)
    tags_json = Column(Text)
    score = Column(Float, default=0.0, nullable=False)
    status = Column(String(30), default="new", nullable=False, index=True)
    reject_reason = Column(Text)
    external_id = Column(String(255))

    sent_item = relationship("SentItem", back_populates="candidate", uselist=False)


class SentItem(Base):
    __tablename__ = "sent_items"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(ForeignKey("candidates.id"), nullable=False)
    sent_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    url_hash = Column(String(64), nullable=False, index=True)
    project_key = Column(String(255), index=True)
    author_project_key = Column(String(255), index=True)
    category = Column(String(80), index=True)
    telegram_message_id = Column(String(80))

    candidate = relationship("Candidate", back_populates="sent_item")


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(30), nullable=False)
    source_name = Column(String(80), nullable=False)
    fetched_count = Column(Integer, default=0, nullable=False)
    saved_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text)


class ManualQueue(Base):
    __tablename__ = "manual_queue"

    id = Column(Integer, primary_key=True)
    url = Column(Text, nullable=False)
    source_name = Column(String(80))
    note = Column(Text)
    status = Column(String(30), default="new", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
