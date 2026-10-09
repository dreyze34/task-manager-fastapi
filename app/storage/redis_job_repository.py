import json
from typing import Any

from redis.asyncio import Redis

from app.models.job import Job, JobCreate

class RedisJobRepository:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _serialize(self, job: Job) -> dict[str, str]:
        return {
            "id": str(job.id),
            "type": job.type,
            "payload": json.dumps(job.payload),
            "status": job.status.value,
            "result": json.dumps(job.result),
            "error": json.dumps(job.error),
            "attempts": str(job.attempts)
        }

    def _deserialize(self, data: dict[str, Any]):
        return Job(
            id=data["id"],
            type=data["type"],
            payload=json.loads(data["payload"]),
            status=data["status"],
            result=json.loads(data["result"]),
            error=json.loads(data["error"]),
            attempts=int(data["attempts"])
        )

    async def _save(self, job: Job) -> None:
        await self.redis.hset(
            f"job:{job.id}",
            mapping=self._serialize(job)
        )

    async def create(self, job: Job) -> None:
        return await self._save(job)

    async def update(self, job: Job) -> None:
        await self._save(job)

    async def get(self, job_id: str):
        data = await self.redis.hgetall(
            f"job:{job_id}"
        )
        if not data:
            return
        return self._deserialize(data)

    async def get_all(self):
        jobs = []
        async for key in self.redis.scan_iter(match="job:*", _type="hash"):
            job = await self.redis.hgetall(key)
            jobs.append(self._deserialize(job))
        return jobs