from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from . import Base

class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    event_data = Column(JSON)
