from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"

class JobCreate(BaseModel):
    type: str
    payload: dict[str, Any]

class Job(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str
    payload: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None
    attempts: int = Field(default=0, ge=0)
