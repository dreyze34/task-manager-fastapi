import asyncio
import logging
import os
from uuid import uuid4

from redis.asyncio import Redis

from app.queue.redis_job_queue import RedisJobQueue
from app.services.worker_service import WorkerService
from app.storage.redis_job_repository import RedisJobRepository
from app.workers.workers import Worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

async def main() -> None:
    redis = Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=5
    )

    try:
        await redis.ping()

        repository = RedisJobRepository(redis)
        queue = RedisJobQueue(
            redis,
            s_name="jobs:queue",
            wg_name="workers",
        )
        await queue.initialize()

        service = WorkerService(repository, queue)
        worker = Worker(
            worker_id=f"worker-{uuid4()}",
            worker_service=service,
        )

        await worker.run()
    finally:
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass