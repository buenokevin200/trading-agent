"""Task schema — work items routed through the kanban board."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    REVIEW = "review"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 20


@dataclass(frozen=True)
class Task:
    schema_version: str = "1.0"
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    objective: str = ""
    assignee: str = ""  # profile name
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    acceptance_criteria: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mode: str = "simulation"  # simulation | paper | real
    parent_task_id: Optional[str] = None
    # correlation
    signal_id: Optional[str] = None
    order_id: Optional[str] = None
    # blocking
    block_reason: Optional[str] = None

    def __post_init__(self):
        if not self.objective:
            raise ValueError("Task objective is required")
        if not self.assignee:
            raise ValueError("Task assignee is required")
