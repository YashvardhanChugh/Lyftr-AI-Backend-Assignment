from pydantic import BaseModel, Field, validator
from typing import Optional
import re
from datetime import datetime

E164_RE = re.compile(r"^\+\d+$")

class WebhookPayload(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias='from')
    to: str = Field(...)
    ts: str = Field(...)
    text: Optional[str] = Field(None, max_length=4096)

    @validator('from_')
    def check_from(cls, v):
        if not E164_RE.match(v):
            raise ValueError('must be E.164-like')
        return v

    @validator('to')
    def check_to(cls, v):
        if not E164_RE.match(v):
            raise ValueError('must be E.164-like')
        return v

    @validator('ts')
    def check_ts(cls, v):
        # ISO-8601 UTC timestamp with Z suffix
        try:
            if not v.endswith('Z'):
                raise ValueError('must end with Z')
            datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            raise ValueError('invalid ts format, expected YYYY-MM-DDTHH:MM:SSZ')
        return v

    class Config:
        allow_population_by_field_name = True


class MessageOut(BaseModel):
    message_id: str
    from_msisdn: str
    to_msisdn: str
    ts: str
    text: Optional[str]
    created_at: str


class MessagesList(BaseModel):
    data: list[MessageOut]
    total: int
    limit: int
    offset: int


class StatsOut(BaseModel):
    total_messages: int
    senders_count: int
    messages_per_sender: list[dict]
    first_message_ts: Optional[str]
    last_message_ts: Optional[str]
