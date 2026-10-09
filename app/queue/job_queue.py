from dataclasses import dataclass
from typing import Protocol

from app.models.job import Job

@dataclass(frozen=True)
class JobMessage:
    job_id: str
    message_id: str

class JobQueue(Protocol):
    async def enqueue(self, job_id: str) -> None: ...
    async def dequeue(self, consumer: str) -> JobMessage | None: ...
    async def acknowledge(self, message_id: str) -> None: ...