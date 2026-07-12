import enum
from datetime import datetime
from typing import TypeAlias

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Status(enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


ScrapeStatus: TypeAlias = Status
ProcessStatus: TypeAlias = Status


class ScrTargetTable(Base):
    """
    Target to run scraper against.
    The scraper will run against the `url` value on periodic interval defined in `schedule_cron` 
    and produce output in `scr_runs` (scraper runs) table.
    """
    __tablename__ = "scr_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # next wall-clock instant this target is eligible to run.
    # computed from schedule_cron on insert and on release. set to now() for "run now".
    # NULL = one-shot, run immediately, never reschedule.
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # populated while a worker holds the row. NULL = free to claim.
    # claimed_by is hostname:pid, kept for observability + the reaper.
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(255))
    carrier_id: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


# runs appear every time a scrape is performed and are later claimed by processor
class ScrRunTable(Base):
    """
    When scraper puts row with `should_process = True` in this table, it becomes eligible for processing.
    Processing is an action of taking `o_filepath` and running processor on it.
    Runs with `should_process = False` represent scraper runs that resulted in the same file as the
    previus run for a target, scraper runs that performed actions with custom scripts etc.
    """
    __tablename__ = "scr_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scr_targets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ScrapeStatus] = mapped_column(
        Enum(ScrapeStatus, name="scrape_status"),
        nullable=False,
        default=ScrapeStatus.pending,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # False = scrape produced no diff vs previous run, processor should skip it.
    # decided at scrape-finish so the processor never diffs at pop time.
    should_process: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_by: Mapped[str | None] = mapped_column(String(255))
    o_filepath: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ScrProcessedTable(Base):
    __tablename__ = "scr_processed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scr_runs.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scr_targets.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ProcessStatus] = mapped_column(
        Enum(ProcessStatus, name="process_status"),
        nullable=False,
        default=ProcessStatus.pending,
    )
    o_filepath: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApiUserTable(Base):
    __tablename__ = "scr_api_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
