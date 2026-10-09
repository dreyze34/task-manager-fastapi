from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.job import Job, JobCreate
from app.queue.redis_job_queue import RedisJobQueue
from app.storage.redis_job_repository import RedisJobRepository
from app.services.job_service import JobService

from app.dependencies import get_job_service

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

ServiceDep = Annotated[JobService, Depends(get_job_service)]

@router.get("")
def get_jobs(
    service: ServiceDep
):
    pass

@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    service: ServiceDep
):
    job = await service.get_job(job_id)
    return job

@router.post("", response_model=Job)
async def create_job(
    request: JobCreate,
    service: ServiceDep
):
    job = await service.create_job(request)
    return job


