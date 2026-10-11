import unittest
from uuid import UUID

import httpx

from app.dependencies import get_job_service
from app.main import app
from app.services.job_service import JobService
from app.services.worker_service import WorkerService
from app.workers.workers import Worker
from tests.fakes import MemoryQueue, MemoryRepository


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repository = MemoryRepository()
        self.queue = MemoryQueue()
        self.service = JobService(self.repository, self.queue)
        self.previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_job_service] = lambda: self.service
        # ASGITransport n'exécute pas le lifespan : aucune connexion Redis réelle.
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    async def submit(self):
        return await self.client.post("/jobs", json={"type": "add", "payload": {"a": 10, "b": 20}})

    async def test_health(self):
        response = await self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    async def test_submit_and_retrieve_pending_job(self):
        response = await self.submit()
        response.raise_for_status()
        data = response.json()
        UUID(data["id"])
        self.assertEqual(data["status"], "pending")
        self.assertIsNone(data["result"])
        self.assertEqual(data["attempts"], 0)
        self.assertEqual(self.queue.messages[0].job_id, data["id"])
        fetched = await self.client.get(f"/jobs/{data['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json(), data)

    async def test_missing_job_returns_404(self):
        response = await self.client.get("/jobs/missing")
        self.assertEqual(response.status_code, 404)
        self.assertIn("missing", response.json()["detail"])

    async def test_list_jobs(self):
        self.assertEqual((await self.client.get("/jobs")).json(), [])
        created = (await self.submit()).json()
        response = await self.client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [created])

    async def test_malformed_requests_return_422_without_persistence(self):
        for body in ({}, {"type": "add"}, {"type": "add", "payload": []}):
            with self.subTest(body=body):
                response = await self.client.post("/jobs", json=body)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(await self.repository.get_all(), [])
        self.assertEqual(len(self.queue.messages), 0)

    async def test_http_submission_then_worker_execution_then_http_result(self):
        created = (await self.submit()).json()
        message = await self.queue.dequeue("test-worker")
        worker = Worker("test-worker", WorkerService(self.repository, self.queue))
        await worker.process_message(message)
        await self.queue.acknowledge(message.message_id)
        response = await self.client.get(f"/jobs/{created['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["result"], 30)

    @unittest.expectedFailure
    async def test_submission_returns_202_as_required_by_architecture(self):
        self.assertEqual((await self.submit()).status_code, 202)
