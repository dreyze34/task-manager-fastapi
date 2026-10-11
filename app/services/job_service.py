from typing import Any

from app.models.job import Job, JobCreate, JobStatus

from app.storage.job_repository import JobRepository
from app.queue.job_queue import JobQueue, JobMessage
from app.workers.handlers import HANDLERS

from app.exceptions import JobNotFoundError, InvalidJobTypeError

class JobService:
    def __init__(self, repository: JobRepository, queue: JobQueue):
        self.repository = repository
        self.queue = queue

    def validate_job(self, type: str, payload):
        if type not in HANDLERS:
            raise InvalidJobTypeError

    async def create_job(self, request: JobCreate) -> Job:
        self.validate_job(request.type, request.payload)

        job = Job(
            type=request.type,
            payload=request.payload
        )

        await self.repository.create(job)
        await self.queue.enqueue(str(job.id))

        return job

    async def get_job(self, job_id: str) -> Job:
        job = await self.repository.get(job_id)
        if not job:
            raise JobNotFoundError(job_id)
        return job

    async def get_jobs(self) -> list[Job]:
        jobs = await self.repository.get_all()
        return jobs