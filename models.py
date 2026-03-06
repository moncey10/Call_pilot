from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from db import Base

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String, unique=True, index=True, nullable=False)
    from_number = Column(String, index=True)
    caller_name = Column(String, default="")
    reason = Column(Text, default="")
    urgency = Column(String, default="unknown")  # low/medium/high/unknown
    transferred = Column(Boolean, default=False)
    recording_url = Column(Text, default="")
    transcript = Column(Text, default="")
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)