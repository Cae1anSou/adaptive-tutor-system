# backend/app/schemas/participant.py
from pydantic import BaseModel
from typing import Optional

class ParticipantBase(BaseModel):
    id: str
    group: str

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantUpdate(BaseModel):
    group: Optional[str] = None

class ParticipantInDBBase(ParticipantBase):
    class Config:
        orm_mode = True

class Participant(ParticipantInDBBase):
    pass