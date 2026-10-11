from collections import deque

from app.models.job import Job
from app.queue.job_queue import JobMessage


class MemoryRepository:
    """Copie les objets pour reproduire la séparation avec le stockage."""

    def __init__(self):
        self.jobs = {}
        self.events = []

    async def create(self, job: Job):
        self.jobs[str(job.id)] = job.model_copy(deep=True)
        self.events.append(("saved", job.status))

    async def update(self, job: Job):
        await self.create(job)

    async def get(self, job_id: str):
        job = self.jobs.get(job_id)
        return job.model_copy(deep=True) if job else None

    async def get_all(self):
        return [job.model_copy(deep=True) for job in self.jobs.values()]


class MemoryQueue:
    def __init__(self):
        self.messages = deque()
        self.acknowledged = []

    async def enqueue(self, job_id: str):
        self.messages.append(JobMessage(job_id, f"{len(self.messages) + 1}-0"))

    async def dequeue(self, consumer: str):
        return self.messages.popleft() if self.messages else None

    async def acknowledge(self, message_id: str):
        self.acknowledged.append(message_id)
