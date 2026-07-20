from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .connection import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    upload_timestamp = Column(DateTime, nullable=False)
    meeting_date = Column(String(50), nullable=True)
    raw_summary = Column(Text, nullable=False)
    key_topics = Column(Text, nullable=False)  # Stored as serialized JSON list string

    # Relationships
    action_items = relationship("ActionItem", back_populates="meeting", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="meeting", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="meeting", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="meeting", cascade="all, delete-orphan")

class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    task = Column(Text, nullable=False)
    owner = Column(String(255), nullable=True)
    deadline = Column(String(255), nullable=True)
    source_chunk = Column(Integer, nullable=False)

    meeting = relationship("Meeting", back_populates="action_items")

class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    decision = Column(Text, nullable=False)
    context = Column(Text, nullable=False)
    source_chunk = Column(Integer, nullable=False)

    meeting = relationship("Meeting", back_populates="decisions")

class Risk(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    risk = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)  # low, medium, high
    source_chunk = Column(Integer, nullable=False)

    meeting = relationship("Meeting", back_populates="risks")

class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    deadline_text = Column(Text, nullable=False)
    normalized_date = Column(String(50), nullable=True)
    related_task = Column(Text, nullable=True)

    meeting = relationship("Meeting", back_populates="deadlines")
