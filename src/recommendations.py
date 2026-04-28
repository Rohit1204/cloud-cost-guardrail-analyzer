from __future__ import annotations

from models import Finding, FindingCategory, Priority, Recommendation


SERVICE_PLAYBOOKS = [
    {
        "tokens": ("ec2", "elastic compute", "compute"),
        "action": "Validate instance rightsizing, scheduling, and commitment coverage for the EC2 spend driver.",
        "steps": [
            "Open Cost Explorer for EC2 grouped by Instance Type, Usage Type, and Purchase Option.",
            "Check Compute Optimizer for rightsizing and idle recommendations.",
            "For steady production usage, evaluate Savings Plans instead of only on-demand instances.",
            "For non-production usage, add start/stop schedules and owner expiry tags.",
        ],
    },
    {
        "tokens": ("s3", "simple storage"),
        "action": "Review S3 storage class, lifecycle, request, and data transfer patterns.",
        "steps": [
            "Open Cost Explorer for S3 grouped by Usage Type to separate storage, requests, and transfer.",
            "Enable S3 Storage Lens or review bucket metrics for large or stale objects.",
            "Add lifecycle policies for infrequent access, Glacier transitions, and incomplete multipart uploads.",
            "Check cross-region replication and public data transfer before changing storage classes.",
        ],
    },
    {
        "tokens": ("rds", "relational database", "aurora"),
        "action": "Review database sizing, storage, Multi-AZ, and reserved capacity for the RDS spend driver.",
        "steps": [
            "Open Cost Explorer grouped by Instance Type, Deployment Option, and Database Engine.",
            "Check CPU, connections, storage growth, IOPS, and backup retention before resizing.",
            "For steady production databases, evaluate Reserved Instances or Aurora capacity planning.",
            "For non-production databases, add stop schedules and shorter backup retention where safe.",
        ],
    },
    {
        "tokens": ("nat gateway", "vpc", "data transfer", "bandwidth"),
        "action": "Investigate network egress, NAT Gateway processing, and cross-AZ or cross-region traffic.",
        "steps": [
            "Group Cost Explorer by Usage Type to find NAT Gateway hours, data processing, or regional transfer.",
            "Check VPC Flow Logs or workload metrics for high-egress sources.",
            "Use VPC endpoints for AWS service traffic that currently leaves through NAT.",
            "Reduce cross-AZ chatter by aligning chatty services and databases in the same AZ where appropriate.",
        ],
    },
    {
        "tokens": ("cloudwatch", "logs"),
        "action": "Review CloudWatch Logs ingestion, retention, custom metrics, and high-cardinality dimensions.",
        "steps": [
            "Group Cost Explorer by Usage Type to separate log ingestion, storage, metrics, and alarms.",
            "Set log retention on noisy log groups and reduce debug logging in production.",
            "Review custom metrics and high-cardinality dimensions that multiply metric costs.",
            "Export long-retention logs to S3 if compliance requires archival storage.",
        ],
    },
    {
        "tokens": ("lambda",),
        "action": "Review Lambda duration, memory sizing, concurrency, and request volume.",
        "steps": [
            "Group Cost Explorer by Usage Type to compare requests, duration, and provisioned concurrency.",
            "Use Lambda Power Tuning to find a better memory and duration balance.",
            "Check retry storms, async failures, and event source batch sizes.",
            "Disable provisioned concurrency where low latency is not required.",
        ],
    },
    {
        "tokens": ("ebs", "elastic block store"),
        "action": "Review EBS volume type, unattached storage, snapshots, and provisioned IOPS.",
        "steps": [
            "Group Cost Explorer by Usage Type to identify gp2/gp3 storage, snapshots, and provisioned IOPS.",
            "Migrate suitable gp2 volumes to gp3 and right-size provisioned IOPS or throughput.",
            "Delete unattached volumes after snapshot validation.",
            "Add snapshot lifecycle policies to expire stale backups.",
        ],
    },
]


def _money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:.2f}/month"


def _dollars(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:.2f}"


def _environment(finding: Finding) -> str:
    return str(finding.metadata.get("environment") or "").lower()


def _owner_hint(finding: Finding) -> str:
    owner = finding.metadata.get("owner")
    owner_email = finding.metadata.get("owner_email")
    if owner and owner_email:
        return f"Route validation to {owner} ({owner_email})."
    if owner_email:
        return f"Route validation to {owner_email}."
    return "Add owner tags before remediation so the right team validates the change."


def _is_production(finding: Finding) -> bool:
    return _environment(finding) in {"prod", "production", "prd"}


def _priority_from_savings(finding: Finding, default: Priority) -> Priority:
    savings = finding.estimated_monthly_savings or 0
    if savings >= 250:
        return Priority.CRITICAL
    if savings >= 25:
        return Priority.WARNING
    return default


def _service_playbook(service_name: str) -> dict[str, object]:
    normalized = service_name.lower()
    for playbook in SERVICE_PLAYBOOKS:
        if any(token in normalized for token in playbook["tokens"]):
            return playbook
    return {
        "action": "Review the service-specific cost dimensions and confirm whether the spend matches expected workload demand.",
        "steps": [
            "Open Cost Explorer filtered to this service and group by Usage Type, Operation, Region, and Resource where available.",
            "Compare the trend with recent deployments, traffic changes, backups, and data transfer patterns.",
            "Create an owner action item for the highest usage type instead of applying a generic optimization.",
        ],
    }


def _top_service_summary(finding: Finding) -> str:
    top_services = finding.metadata.get("top_services") or []
    if not top_services:
        return "Top service contributors were not available in the detector metadata."
    parts = []
    for item in top_services[:3]:
        if isinstance(item, dict):
            parts.append(f"{item.get('service', 'Unknown')} ({_dollars(float(item.get('amount', 0)))})")
    return "Top contributors: " + ", ".join(parts) if parts else "Top service contributors were not available."


def recommendation_for(finding: Finding) -> Recommendation:
    if finding.category == FindingCategory.IDLE_EC2:
        instance_type = finding.metadata.get("instance_type", "unknown type")
        env = _environment(finding) or "unspecified"
        action = (
            "Validate dependency and downsize instead of stopping immediately because this appears to be production."
            if _is_production(finding)
            else "Stop or schedule this EC2 instance if the owner confirms it is not needed continuously."
        )
        return Recommendation(
            finding=finding,
            priority=Priority.WARNING,
            action=action,
            rationale=(
                f"The {instance_type} instance averaged {finding.metric_value:.2f}% CPU, below the "
                f"{finding.threshold:.2f}% threshold in the {env} environment."
            ),
            next_steps=[
                _owner_hint(finding),
                "Check CloudWatch CPU, network, and status checks before taking action.",
                f"Non-production stop command: aws ec2 stop-instances --instance-ids {finding.resource_id}",
                "If it is required, resize it or tag it with CostGuardrail=Ignore and an expiry date.",
            ],
        )

    if finding.category == FindingCategory.UNATTACHED_EBS:
        size_gib = finding.metadata.get("size_gib")
        volume_type = finding.metadata.get("volume_type", "unknown")
        return Recommendation(
            finding=finding,
            priority=_priority_from_savings(finding, Priority.WARNING),
            action="Snapshot the volume if data must be retained, then delete the unattached volume.",
            rationale=(
                f"The {volume_type} volume is detached, still billed, and estimated to save "
                f"{_money(finding.estimated_monthly_savings)}. Size: {size_gib or 'unknown'} GiB."
            ),
            next_steps=[
                _owner_hint(finding),
                f"Create a final snapshot: aws ec2 create-snapshot --volume-id {finding.resource_id}",
                f"Delete after validation: aws ec2 delete-volume --volume-id {finding.resource_id}",
                "Check AMIs, launch templates, and backup policies before deleting.",
            ],
        )

    if finding.category == FindingCategory.IDLE_RDS:
        env = _environment(finding) or "unspecified"
        avg_cpu = finding.metadata.get("avg_cpu", 0)
        avg_connections = finding.metadata.get("avg_connections", 0)
        return Recommendation(
            finding=finding,
            priority=Priority.CRITICAL if _is_production(finding) else Priority.WARNING,
            action=(
                "Create a database rightsizing plan with rollback because this idle database is tagged as production."
                if _is_production(finding)
                else "Stop, schedule, or downsize this idle database after confirming no active dependency."
            ),
            rationale=(
                f"The database averaged {float(avg_cpu):.2f}% CPU and {float(avg_connections):.2f} connections "
                f"in the {env} environment, indicating over-provisioned capacity."
            ),
            next_steps=[
                _owner_hint(finding),
                "Confirm backup status, maintenance window, Multi-AZ setting, and application dependency.",
                f"Non-production stop command: aws rds stop-db-instance --db-instance-identifier {finding.resource_id}",
                "For production, test a smaller instance class or storage configuration in a lower environment first.",
            ],
        )

    if finding.category == FindingCategory.SPEND_SPIKE:
        baseline = finding.metadata.get("baseline_daily_cost")
        increase = finding.metadata.get("increase")
        return Recommendation(
            finding=finding,
            priority=Priority.CRITICAL,
            action="Investigate the top spend contributors and recent workload changes before changing thresholds.",
            rationale=(
                f"Daily spend reached {_dollars(finding.metric_value)} versus a "
                f"{_dollars(float(baseline)) if baseline is not None else 'unknown'} baseline. "
                f"Increase: {_dollars(float(increase)) if increase is not None else 'unknown'}. "
                f"{_top_service_summary(finding)}"
            ),
            next_steps=[
                _owner_hint(finding),
                "Open Cost Explorer grouped by Service and Usage Type for the spike date.",
                "Check recent deployments, autoscaling events, NAT Gateway transfer, backups, and new high-cardinality logs.",
                "If the driver is expected growth, update budget thresholds; otherwise create an incident for the owning team.",
            ],
        )

    if finding.category == FindingCategory.HIGH_COST_SERVICE:
        playbook = _service_playbook(finding.resource_id)
        lookback_days = finding.metadata.get("lookback_days", "the lookback window")
        return Recommendation(
            finding=finding,
            priority=Priority.WARNING if finding.metric_value >= finding.threshold * 2 else Priority.INFO,
            action=str(playbook["action"]),
            rationale=(
                f"{finding.resource_id} spent {_dollars(finding.metric_value)} over {lookback_days} days, "
                f"against a {_dollars(finding.threshold)} review threshold. The recommendation is selected "
                "from the service family and spend context rather than a generic rule."
            ),
            next_steps=[
                _owner_hint(finding),
                *list(playbook["steps"]),
            ],
        )

    return Recommendation(
        finding=finding,
        priority=Priority.INFO,
        action="Review this finding and decide whether it should be remediated or exempted.",
        rationale=finding.description,
        next_steps=["Add ownership tags so future recommendations can route to the right team."],
    )


def build_recommendations(findings: list[Finding]) -> list[Recommendation]:
    return [recommendation_for(finding) for finding in findings]
