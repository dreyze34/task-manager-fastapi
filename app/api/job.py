from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.job import Job, JobCreate
from app.queue.redis_job_queue import RedisJobQueue
from app.storage.redis_job_repository import RedisJobRepository

from app.dependencies import get_queue, get_repository

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"]
)

RepoServiceDep = Annotated[RedisJobRepository, Depends(get_repository)]

@router.get("")
def get_jobs(
    repository: RepoServiceDep
):
    pass

@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    repository: RepoServiceDep
):
    job = await repository.get(job_id)
    return job

@router.post("", response_model=Job)
async def create_job(
    job_create: JobCreate,
    repository: RepoServiceDep
):
    job = Job(
        type=job_create.type,
        payload=job_create.payload
    )
    await repository.create(job)
    return job


