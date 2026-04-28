from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Priority(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FindingCategory(str, Enum):
    IDLE_EC2 = "idle_ec2"
    UNATTACHED_EBS = "unattached_ebs"
    IDLE_RDS = "idle_rds"
    SPEND_SPIKE = "spend_spike"
    HIGH_COST_SERVICE = "high_cost_service"


@dataclass(frozen=True)
class Finding:
    category: FindingCategory
    resource_id: str
    resource_type: str
    region: str
    title: str
    description: str
    metric_name: str
    metric_value: float
    threshold: float
    estimated_monthly_savings: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Recommendation:
    finding: Finding
    priority: Priority
    action: str
    rationale: str
    next_steps: list[str]


@dataclass(frozen=True)
class NotificationResult:
    channel: str
    delivered: bool
    detail: str
