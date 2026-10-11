import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.models.job import Job, JobStatus
from app.queue.job_queue import JobMessage
from app.services.worker_service import WorkerService
from app.workers.workers import Worker
from tests.fakes import MemoryQueue, MemoryRepository


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = MemoryRepository()
        self.queue = MemoryQueue()
        self.service = WorkerService(self.repository, self.queue)
        self.worker = Worker("test-worker", self.service)

    async def run_one(self, job, *, idle_first=False):
        await self.repository.create(job)
        message = JobMessage(str(job.id), "1-0")
        reads = [message, asyncio.CancelledError()]
        if idle_first:
            reads.insert(0, None)
        self.queue.dequeue = AsyncMock(side_effect=reads)

        async def acknowledge(message_id):
            saved = await self.repository.get(str(job.id))
            self.assertIn(saved.status, (JobStatus.COMPLETED, JobStatus.FAILED))
            self.queue.acknowledged.append(message_id)

        self.queue.acknowledge = AsyncMock(side_effect=acknowledge)
        with self.assertRaises(asyncio.CancelledError):
            await self.worker.run()
        return await self.repository.get(str(job.id))

    async def test_success_is_saved_before_acknowledgment(self):
        job = await self.run_one(Job(type="add", payload={"a": 10, "b": 20}), idle_first=True)
        self.assertEqual(job.result, 30)
        self.assertEqual(job.attempts, 1)
        self.assertEqual(self.queue.acknowledged, ["1-0"])
        self.queue.dequeue.assert_awaited_with("test-worker")

    async def test_handler_failure_is_saved_then_acknowledged_without_traceback(self):
        with self.assertLogs("app.workers.workers", level="ERROR") as logs:
            job = await self.run_one(Job(type="fibonacci", payload={"n": -1}))
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertIn("non-negative", job.error)
        self.assertEqual(self.queue.acknowledged, ["1-0"])
        self.assertTrue(all(record.exc_info is None for record in logs.records))

    async def test_terminal_jobs_are_not_executed_again(self):
        for status in (JobStatus.COMPLETED, JobStatus.FAILED):
            with self.subTest(status=status):
                self.queue.acknowledged.clear()
                with patch.object(self.worker, "execute_job", new_callable=AsyncMock) as execute:
                    saved = await self.run_one(Job(type="add", payload={}, status=status))
                execute.assert_not_awaited()
                self.assertEqual(saved.status, status)
                self.assertEqual(self.queue.acknowledged, ["1-0"])

    async def test_storage_failure_propagates_without_acknowledgment(self):
        job = Job(type="add", payload={"a": 1, "b": 2})
        await self.repository.create(job)
        self.queue.dequeue = AsyncMock(return_value=JobMessage(str(job.id), "1-0"))
        self.service.complete_job = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
        self.service.fail_job = AsyncMock()
        with self.assertRaises(ConnectionError):
            await self.worker.run()
        self.assertEqual(self.queue.acknowledged, [])
        self.service.fail_job.assert_not_awaited()

    async def test_failed_state_write_failure_prevents_acknowledgment(self):
        job = Job(type="fibonacci", payload={"n": -1})
        await self.repository.create(job)
        self.queue.dequeue = AsyncMock(return_value=JobMessage(str(job.id), "1-0"))
        self.service.fail_job = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
        with self.assertLogs("app.workers.workers", level="ERROR"):
            with self.assertRaises(ConnectionError):
                await self.worker.run()
        self.assertEqual(self.queue.acknowledged, [])

    async def test_execution_does_not_block_event_loop(self):
        import threading

        loop_thread = threading.get_ident()
        with patch("app.workers.workers.execute", side_effect=lambda job: threading.get_ident()):
            handler_thread = await self.worker.execute_job(Job(type="add", payload={}))
        self.assertNotEqual(handler_thread, loop_thread)
