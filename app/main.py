from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.storage.redis_job_repository import RedisJobRepository
from app.queue.redis_job_queue import RedisJobQueue
from app.services.job_service import JobService

from app.api import jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(
        "redis://localhost:6379/0",
        decode_responses=True,
    )
    try:
        await redis.ping()

        repository = RedisJobRepository(redis)
        queue = RedisJobQueue(redis, s_name="jobs:queue", wg_name="workers")
        job_service = JobService(repository, queue)
        app.state.job_service = job_service
        await app.state.job_service.queue.initialize()
        yield
    finally:
        await redis.close()

app = FastAPI(title="Task Manager API", version="0.1.0", lifespan=lifespan)

app.include_router(jobs.router)

@app.get("/health")
def health():
    return {
        "status": "ok"
    }