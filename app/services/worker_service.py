from typing import Any
from app.models.job import Job, JobCreate, JobStatus

from app.storage.job_repository import JobRepository
from app.queue.job_queue import JobQueue

from app.exceptions import JobNotFoundError, InvalidJobStatusError


class WorkerService:
    def __init__(self, repository: JobRepository, queue: JobQueue):
        self.repository = repository
        self.queue = queue

    async def get_job(self, job_id: str) -> Job:
        job = await self.repository.get(job_id)
        if not job:
            raise JobNotFoundError(job_id)
        return job
    
    async def mark_running(self, job_id: str) -> bool:
        job = await self.get_job(job_id)

        if job.status != JobStatus.PENDING:
            raise InvalidJobStatusError(job_id)
        
        job.status = JobStatus.RUNNING
        job.attempts += 1
        await self.repository.update(job)
        return True

    async def complete_job(self, job_id: str, result: Any) -> bool:
        job = await self.get_job(job_id)

        if job.status != JobStatus.RUNNING:
            raise InvalidJobStatusError(job_id)
        
        job.status = JobStatus.COMPLETED
        job.result = result
        await self.repository.update(job)
        return True

    async def fail_job(self, job_id: str, error: str) -> bool:
        job = await self.get_job(job_id)

        if job.status != JobStatus.RUNNING:
            raise InvalidJobStatusError(job_id)
        
        job.status = JobStatus.FAILED
        job.error = error
        await self.repository.update(job)
        return True

    async def acknowledge_message(self, message_id: str):
        await self.queue.acknowledge(message_id)
        return True