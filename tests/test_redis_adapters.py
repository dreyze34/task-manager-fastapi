import unittest
from unittest.mock import AsyncMock, Mock

from redis.exceptions import ResponseError

from app.models.job import Job, JobStatus
from app.queue.job_queue import JobMessage
from app.queue.redis_job_queue import RedisJobQueue
from app.storage.redis_job_repository import RedisJobRepository


class QueueTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis = Mock()
        for name in ("xgroup_create", "xadd", "xreadgroup", "xack"):
            setattr(self.redis, name, AsyncMock())
        self.queue = RedisJobQueue(self.redis, "jobs:queue", "workers")

    async def test_initialize_creates_group_from_start_and_missing_stream(self):
        await self.queue.initialize()
        self.redis.xgroup_create.assert_awaited_once_with(
            name="jobs:queue", groupname="workers", id="0", mkstream=True
        )

    async def test_initialize_accepts_existing_group(self):
        self.redis.xgroup_create.side_effect = ResponseError("BUSYGROUP Consumer Group name already exists")
        await self.queue.initialize()

    async def test_initialize_does_not_hide_other_errors(self):
        self.redis.xgroup_create.side_effect = ResponseError("WRONGTYPE")
        with self.assertRaises(ResponseError):
            await self.queue.initialize()

    async def test_enqueue_transmits_business_id(self):
        await self.queue.enqueue("job-123")
        self.redis.xadd.assert_awaited_once_with("jobs:queue", {"job_id": "job-123"})

    async def test_dequeue_distinguishes_job_and_message_identifiers(self):
        self.redis.xreadgroup.return_value = [("jobs:queue", [("42-0", {"job_id": "job-123"})])]
        self.assertEqual(await self.queue.dequeue("worker-1"), JobMessage("job-123", "42-0"))
        self.redis.xreadgroup.assert_awaited_once_with(
            groupname="workers", consumername="worker-1",
            streams={"jobs:queue": ">"}, count=1, block=5000
        )

    async def test_empty_read_returns_none(self):
        self.redis.xreadgroup.return_value = []
        self.assertIsNone(await self.queue.dequeue("worker-1"))

    async def test_acknowledge_uses_message_identifier(self):
        await self.queue.acknowledge("42-0")
        self.redis.xack.assert_awaited_once_with("jobs:queue", "workers", "42-0")


class RepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hashes = {}
        self.redis = Mock()

        async def hset(key, mapping):
            self.hashes.setdefault(key, {}).update(mapping)

        async def hgetall(key):
            return self.hashes.get(key, {}).copy()

        async def scan_iter(**kwargs):
            for key in self.hashes:
                yield key

        self.redis.hset = AsyncMock(side_effect=hset)
        self.redis.hgetall = AsyncMock(side_effect=hgetall)
        self.redis.scan_iter = Mock(side_effect=scan_iter)
        self.repository = RedisJobRepository(self.redis)

    async def test_round_trip_preserves_json_types_and_nulls(self):
        for result in (None, 30, [2, 3], {"valid": True}, "text"):
            with self.subTest(result=result):
                job = Job(type="add", payload={"a": 1, "nested": [True, None]}, result=result)
                await self.repository.create(job)
                self.assertEqual(await self.repository.get(str(job.id)), job)
                self.assertTrue(all(isinstance(v, str) for v in self.hashes[f"job:{job.id}"].values()))

    async def test_missing_job_returns_none(self):
        self.assertIsNone(await self.repository.get("missing"))

    async def test_update_persists_status_result_error_and_attempts(self):
        job = Job(type="add", payload={})
        await self.repository.create(job)
        job.status = JobStatus.FAILED
        job.error = "handler error"
        job.attempts = 1
        await self.repository.update(job)
        self.assertEqual(await self.repository.get(str(job.id)), job)

    async def test_list_reconstructs_all_jobs(self):
        self.assertEqual(await self.repository.get_all(), [])
        job = Job(type="add", payload={})
        await self.repository.create(job)
        self.assertEqual(await self.repository.get_all(), [job])
        self.redis.scan_iter.assert_called_with(match="job:*", _type="hash")
