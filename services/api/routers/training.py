import uuid
import asyncio
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from core.database import get_db, TrainingJob, JobStatus
from schemas.training import TrainingJobCreate, TrainingJobResponse
from services.training_runner import start_training_job

router = APIRouter(prefix="/api/v1/training", tags=["training"])


@router.post("/jobs", response_model=TrainingJobResponse)
async def create_training_job(body: TrainingJobCreate, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())[:8]
    job = TrainingJob(
        id=job_id,
        dataset_id=body.dataset_id,
        task_type=body.task_type,
        model_size=body.model_size,
        epochs=body.epochs,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # training_runner creates its own session — do NOT pass db across thread boundary
    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        None,
        start_training_job,
        job_id, body.dataset_id, body.task_type,
        body.model_size, body.epochs, body.class_names,
    )

    return job


@router.get("/jobs", response_model=List[TrainingJobResponse])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(TrainingJob).order_by(TrainingJob.created_at.desc()).all()


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/logs")
def stream_logs(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job or not job.log_path:
        raise HTTPException(status_code=404, detail="Log not found")

    log_path = Path(job.log_path)
    # Support SSE resume: skip lines already sent to avoid duplicates on reconnect
    last_id_raw = request.headers.get("Last-Event-ID", "")
    skip_lines = int(last_id_raw) + 1 if last_id_raw.isdigit() else 0
    is_done = job.status not in (JobStatus.running, JobStatus.pending)

    def generate():
        if not log_path.exists():
            yield "data: Log file not ready yet\n\n"
            return

        line_num = 0
        with log_path.open("r", errors="replace") as f:
            for raw_line in f:
                if line_num >= skip_lines:
                    yield f"id: {line_num}\ndata: {raw_line.rstrip()}\n\n"
                line_num += 1

        # Signal the client to stop reconnecting when the job is finished
        if is_done:
            yield "event: done\ndata: \n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/jobs/{job_id}")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatus.running:
        job.status = JobStatus.cancelled
        db.commit()
    return {"cancelled": job_id}
