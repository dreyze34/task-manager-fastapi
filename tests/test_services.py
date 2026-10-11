import unittest

from app.exceptions import InvalidJobStatusError, JobNotFoundError
from app.models.job import Job, JobCreate, JobStatus
from app.services.job_service import JobService
from app.services.worker_service import WorkerService
from tests.fakes import MemoryQueue, MemoryRepository


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = MemoryRepository()
        self.queue = MemoryQueue()
        self.jobs = JobService(self.repository, self.queue)
        self.worker = WorkerService(self.repository, self.queue)

    async def test_create_persists_and_enqueues_pending_job(self):
        job = await self.jobs.create_job(JobCreate(type="add", payload={"a": 10, "b": 20}))
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.attempts, 0)
        self.assertEqual(await self.repository.get(str(job.id)), job)
        self.assertEqual(self.queue.messages[0].job_id, str(job.id))

    async def test_get_missing_job_raises_domain_error(self):
        for service in (self.jobs, self.worker):
            with self.subTest(service=type(service).__name__):
                with self.assertRaises(JobNotFoundError):
                    await service.get_job("missing")

    async def test_list_empty_and_populated_repository(self):
        self.assertEqual(await self.jobs.get_jobs(), [])
        job = await self.jobs.create_job(JobCreate(type="add", payload={"a": 1, "b": 2}))
        self.assertEqual(await self.jobs.get_jobs(), [job])

    async def test_successful_lifecycle(self):
        job = Job(type="add", payload={"a": 10, "b": 20})
        await self.repository.create(job)
        await self.worker.mark_running(str(job.id))
        running = await self.repository.get(str(job.id))
        self.assertEqual(running.status, JobStatus.RUNNING)
        self.assertEqual(running.attempts, 1)
        await self.worker.complete_job(str(job.id), 30)
        completed = await self.repository.get(str(job.id))
        self.assertEqual(completed.status, JobStatus.COMPLETED)
        self.assertEqual(completed.result, 30)

    async def test_failed_lifecycle_records_error(self):
        job = Job(type="fibonacci", payload={"n": -1})
        await self.repository.create(job)
        await self.worker.mark_running(str(job.id))
        await self.worker.fail_job(str(job.id), "invalid n")
        failed = await self.repository.get(str(job.id))
        self.assertEqual(failed.status, JobStatus.FAILED)
        self.assertEqual(failed.error, "invalid n")

    async def test_invalid_transitions_do_not_change_stored_job(self):
        allowed = {"mark_running": JobStatus.PENDING,
                   "complete_job": JobStatus.RUNNING, "fail_job": JobStatus.RUNNING}
        for method, valid_status in allowed.items():
            for status in JobStatus:
                if status == valid_status:
                    continue
                with self.subTest(method=method, status=status):
                    job = Job(type="add", payload={}, status=status)
                    await self.repository.create(job)
                    args = [str(job.id)]
                    if method != "mark_running":
                        args.append("value")
                    with self.assertRaises(InvalidJobStatusError):
                        await getattr(self.worker, method)(*args)
                    self.assertEqual(await self.repository.get(str(job.id)), job)

    @unittest.expectedFailure
    async def test_unknown_type_is_rejected_before_persistence(self):
        # ARCHITECTURE.md : JobService doit valider les types autorisés.
        with self.assertRaises(ValueError):
            await self.jobs.create_job(JobCreate(type="unknown", payload={}))
        self.assertEqual(await self.repository.get_all(), [])

    @unittest.expectedFailure
    async def test_invalid_add_payload_is_rejected_before_persistence(self):
        # Lacune actuelle : validate_job contient seulement pass.
        with self.assertRaises(ValueError):
            await self.jobs.create_job(JobCreate(type="add", payload={"a": 1}))
        self.assertEqual(await self.repository.get_all(), [])
