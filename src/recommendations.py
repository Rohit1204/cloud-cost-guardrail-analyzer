from __future__ import annotations

from models import Finding, FindingCategory, Priority, Recommendation


def _money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:.2f}/month"


def recommendation_for(finding: Finding) -> Recommendation:
    if finding.category == FindingCategory.IDLE_EC2:
        instance_type = finding.metadata.get("instance_type", "unknown type")
        return Recommendation(
            finding=finding,
            priority=Priority.WARNING,
            action="Stop, resize, or tag this EC2 instance as exempt if it is intentionally idle.",
            rationale=f"The {instance_type} instance is running with CPU below the idle threshold.",
            next_steps=[
                f"Confirm owner and workload for EC2 instance {finding.resource_id}.",
                f"Run: aws ec2 stop-instances --instance-ids {finding.resource_id}",
                "If it is required, resize it or add a CostGuardrail=Ignore tag with an expiry date.",
            ],
        )

    if finding.category == FindingCategory.UNATTACHED_EBS:
        return Recommendation(
            finding=finding,
            priority=Priority.WARNING,
            action="Snapshot the volume if data must be retained, then delete the unattached volume.",
            rationale=f"Detached EBS volumes keep charging while unused. Estimated savings: {_money(finding.estimated_monthly_savings)}.",
            next_steps=[
                f"Create a final snapshot: aws ec2 create-snapshot --volume-id {finding.resource_id}",
                f"Delete after validation: aws ec2 delete-volume --volume-id {finding.resource_id}",
                "Check whether backups or AMIs already retain this data before deleting.",
            ],
        )

    if finding.category == FindingCategory.IDLE_RDS:
        return Recommendation(
            finding=finding,
            priority=Priority.CRITICAL,
            action="Stop the database during idle periods, downsize it, or migrate to a cheaper engine/class.",
            rationale="The database shows both low CPU and low connection count, which usually means capacity is over-provisioned.",
            next_steps=[
                f"Confirm application dependency and backup status for DB {finding.resource_id}.",
                f"Stop if non-production: aws rds stop-db-instance --db-instance-identifier {finding.resource_id}",
                "For production, compare instance class, storage, and Multi-AZ requirements before resizing.",
            ],
        )

    if finding.category == FindingCategory.SPEND_SPIKE:
        return Recommendation(
            finding=finding,
            priority=Priority.CRITICAL,
            action="Investigate the services and resources responsible for the spend spike immediately.",
            rationale="Daily account spend exceeded both the minimum dollar threshold and the baseline multiplier.",
            next_steps=[
                "Open Cost Explorer grouped by Service and Usage Type for the spike date.",
                "Check recent deployments, scaling events, NAT Gateway data transfer, and new storage snapshots.",
                "Create or tighten an AWS Budget alert if this spend pattern is unexpected.",
            ],
        )

    if finding.category == FindingCategory.HIGH_COST_SERVICE:
        return Recommendation(
            finding=finding,
            priority=Priority.INFO,
            action="Review the top cost drivers for this service and apply service-specific optimization.",
            rationale="The service crossed the configured review threshold for the lookback window.",
            next_steps=[
                f"Open Cost Explorer filtered to service: {finding.resource_id}.",
                "Group by Usage Type, Operation, and Linked Account to find the main driver.",
                "Create a follow-up optimization task for the owner of that workload.",
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
