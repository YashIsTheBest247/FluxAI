from fastapi import APIRouter, HTTPException

from ..models.schemas import GenerateRequest, Job
from ..pipeline import submit
from ..storage import clear_pending_jobs, list_jobs, load_job

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=Job)
async def generate(req: GenerateRequest):
    return submit(req)


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@router.get("/jobs", response_model=list[Job])
async def get_jobs(limit: int = 30):
    return list_jobs(limit=limit)


@router.delete("/jobs/pending")
async def clear_pending():
    """Erase queued / in-progress / failed jobs. Completed jobs stay in the library."""
    return {"cleared": clear_pending_jobs()}
