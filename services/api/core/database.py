from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
import enum

DATABASE_URL = "sqlite:////data/mlops.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(String, primary_key=True)
    dataset_id = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    model_size = Column(String, default="yolo11n")
    epochs = Column(Integer, default=100)
    status = Column(SAEnum(JobStatus), default=JobStatus.pending)
    mlflow_run_id = Column(String, nullable=True)
    log_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    error_msg = Column(Text, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
