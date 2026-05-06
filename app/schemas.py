from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class StatusResponse(BaseModel):
    sealed: bool


class UnsealRequest(BaseModel):
    parts: list[str]


class MessageResponse(BaseModel):
    sealed: bool | None = None
    name: str | None = None
    message: str


class SecretUpsertRequest(BaseModel):
    name: str = Field(min_length=1)
    value: str


class SecretResponse(BaseModel):
    name: str
    value: str


class WrapRequest(BaseModel):
    ttl_seconds: int | None = Field(default=None, gt=0)


class WrapResponse(BaseModel):
    token: str
    expires_at: datetime


class UnwrapRequest(BaseModel):
    token: str = Field(min_length=1)
