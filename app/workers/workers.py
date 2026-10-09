import asyncio
import logging

from app.models.job import Job, JobStatus
from app.services.worker_service import WorkerService
from app.queue.redis_job_queue import JobMessage
from app.workers.handlers import execute

logger = logging.getLogger(__name__)

class Worker:
    def __init__(self, worker_id: str, worker_service: WorkerService):
        self.worker_id = worker_id
        self.worker_service = worker_service

    async def run(self):
        logger.info("Started worker: %s", self.worker_id)
        while True:
            message = await self.worker_service.queue.dequeue(
                self.worker_id
            )

            if message is None:
                continue

            await self.process_message(message)
            await self.worker_service.acknowledge_message(message.message_id)
            logger.info("Acknowledged job job_id=%s", message.job_id)


    async def process_message(self, message: JobMessage):
        job = await self.worker_service.get_job(message.job_id)
        if job.status == JobStatus.COMPLETED or job.status == JobStatus.FAILED:
            return
        await self.worker_service.mark_running(message.job_id)
        logger.info("Started job job_id=%s type=%s", message.job_id, job.type)

        try:
            result = await self.execute_job(job)
        except Exception as e:
            logger.error("Handler fail job_id=%s", message.job_id)
            await self.worker_service.fail_job(message.job_id, str(e))
            logger.info("Failed job job_id=%s", message.job_id)
        else:
            await self.worker_service.complete_job(message.job_id, result)
            logger.info("Completed job job_id=%s", message.job_id)

    async def execute_job(self, job: Job):
        try:
            return await asyncio.to_thread(execute, job)
        except Exception as e:
            raise(e)