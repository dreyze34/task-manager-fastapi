import json
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.models.job import Job, JobCreate
from app.queue.job_queue import JobMessage

class RedisJobQueue:
    def __init__(self, redis: Redis, s_name: str, wg_name: str):
        self.redis = redis
        self.s_name = s_name
        self.wg_name = wg_name

    async def initialize(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=self.s_name,
                groupname=self.wg_name,
                id="0",
                mkstream=True
            )
        except ResponseError as exc:
            if not str(exc).startswith("BUSYGROUP"):
                raise

    async def enqueue(self, job_id: str) -> None:
        await self.redis.xadd(
            self.s_name,
            {"job_id": job_id}
        )

    async def dequeue(self, consumer: str) -> JobMessage | None:
        message = await self.redis.xreadgroup(
            groupname=self.wg_name, 
            consumername=consumer,
            streams={self.s_name: ">"},
            count=1,
            block=5000
        )

        if not message:
            return None

        _, entries = message[0]
        message_id, fields = entries[0]

        return JobMessage(
            job_id=fields["job_id"],
            message_id=message_id
        )

    async def acknowledge(self, message_id: str) -> None:
        await self.redis.xack(
            self.s_name,
            self.wg_name,
            message_id
        )