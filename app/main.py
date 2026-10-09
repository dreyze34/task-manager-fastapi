from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.storage.redis_job_repository import RedisJobRepository
from app.queue.redis_job_queue import RedisJobQueue

from app.api import job

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(
        "redis://localhost:6379/0",
        decode_responses=True,
    )
    try:
        await redis.ping()

        app.state.repository = RedisJobRepository(redis=redis)
        app.state.queue = RedisJobQueue(redis=redis, s_name="job:queue", wg_name="workers")
        await app.state.queue.initialize()
        yield
    finally:
        await redis.close()

app = FastAPI(title="Task Manager API", version="0.1.0", lifespan=lifespan)

app.include_router(job.router)

@app.get("/health")
def health():
    return {
        "status": "ok"
    }