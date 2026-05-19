"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uuid_str() -> str:
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    building_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scale_px_per_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_w_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    building_h_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    ceiling_h_m: Mapped[float] = mapped_column(Float, default=3.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    walls: Mapped[list["Wall"]] = relationship(
        backref="project", cascade="all, delete-orphan"
    )
    aps: Mapped[list["AccessPoint"]] = relationship(
        backref="project", cascade="all, delete-orphan"
    )
    runs: Mapped[list["OptimizationRun"]] = relationship(
        backref="project", cascade="all, delete-orphan"
    )


class Wall(Base):
    __tablename__ = "walls"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    p1_x: Mapped[float] = mapped_column(Float)
    p1_y: Mapped[float] = mapped_column(Float)
    p2_x: Mapped[float] = mapped_column(Float)
    p2_y: Mapped[float] = mapped_column(Float)
    material: Mapped[str] = mapped_column(String(20), default="concrete")
    height: Mapped[float] = mapped_column(Float, default=3.0)


class AccessPoint(Base):
    __tablename__ = "access_points"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(50))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float, default=2.7)
    tx_power_dbm: Mapped[float] = mapped_column(Float, default=20.0)
    freq_ghz: Mapped[float] = mapped_column(Float, default=2.4)


class OptimizationRun(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid_str)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    algorithm: Mapped[str] = mapped_column(String(20), default="ga")
    target_coverage: Mapped[float] = mapped_column(Float, default=0.9)
    final_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    num_aps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
