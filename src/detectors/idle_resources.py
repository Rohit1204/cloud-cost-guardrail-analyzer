from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from aws_clients import AwsClientFactory
from config import Settings
from models import Finding, FindingCategory
from ownership import ownership_metadata, tags_to_dict


def _tag_name(tags: list[dict[str, str]] | None) -> str | None:
    return tags_to_dict(tags).get("Name")


def detect_idle_ec2(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    findings: list[Finding] = []
    for instance in factory.list_running_instances():
        instance_id = instance["InstanceId"]
        avg_cpu = factory.average_metric(
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            lookback_days=settings.lookback_days,
        )
        if avg_cpu is None or avg_cpu > settings.idle_cpu_threshold:
            continue
        tags = tags_to_dict(instance.get("Tags"))
        name = tags.get("Name") or instance_id
        findings.append(
            Finding(
                category=FindingCategory.IDLE_EC2,
                resource_id=instance_id,
                resource_type="ec2-instance",
                region=settings.aws_region,
                title=f"Idle EC2 instance: {name}",
                description=(
                    f"Instance {instance_id} averaged {avg_cpu:.2f}% CPU over "
                    f"{settings.lookback_days} days."
                ),
                metric_name="CPUUtilization",
                metric_value=avg_cpu,
                threshold=settings.idle_cpu_threshold,
                metadata={
                    "instance_type": instance.get("InstanceType"),
                    "launch_time": str(instance.get("LaunchTime")),
                    "name": name,
                    **ownership_metadata(tags, settings),
                },
            )
        )
    return findings


def detect_unattached_ebs(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    findings: list[Finding] = []
    now = datetime.now(timezone.utc)
    for volume in factory.list_unattached_volumes():
        created = volume.get("CreateTime")
        age_days = (now - created).days if created else 0
        volume_id = volume["VolumeId"]
        size_gib = float(volume.get("Size", 0))
        tags = tags_to_dict(volume.get("Tags"))
        # gp3 in us-east-1 is commonly around $0.08/GB-month; this is a practical estimate for alerting.
        estimated_monthly_savings = size_gib * 0.08 if size_gib else None
        findings.append(
            Finding(
                category=FindingCategory.UNATTACHED_EBS,
                resource_id=volume_id,
                resource_type="ebs-volume",
                region=settings.aws_region,
                title=f"Unattached EBS volume: {volume_id}",
                description=f"Volume {volume_id} is unattached and has been available for about {age_days} days.",
                metric_name="age_days",
                metric_value=float(age_days),
                threshold=0.0,
                estimated_monthly_savings=estimated_monthly_savings,
                metadata={
                    "size_gib": size_gib,
                    "volume_type": volume.get("VolumeType"),
                    "availability_zone": volume.get("AvailabilityZone"),
                    **ownership_metadata(tags, settings),
                },
            )
        )
    return findings


def detect_idle_rds(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    findings: list[Finding] = []
    for db in factory.list_rds_instances():
        db_id = db["DBInstanceIdentifier"]
        cpu = factory.average_metric(
            namespace="AWS/RDS",
            metric_name="CPUUtilization",
            dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
            lookback_days=settings.lookback_days,
        )
        connections = factory.average_metric(
            namespace="AWS/RDS",
            metric_name="DatabaseConnections",
            dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
            lookback_days=settings.lookback_days,
        )
        if cpu is None or connections is None:
            continue
        if cpu > settings.idle_cpu_threshold or connections > settings.idle_db_connection_threshold:
            continue
        tags = tags_to_dict(db.get("TagList") or db.get("Tags") or factory.rds_tags(db.get("DBInstanceArn")))
        findings.append(
            Finding(
                category=FindingCategory.IDLE_RDS,
                resource_id=db_id,
                resource_type="rds-instance",
                region=settings.aws_region,
                title=f"Idle RDS instance: {db_id}",
                description=(
                    f"RDS instance {db_id} averaged {cpu:.2f}% CPU and "
                    f"{connections:.2f} connections over {settings.lookback_days} days."
                ),
                metric_name="CPUUtilization/DatabaseConnections",
                metric_value=max(cpu, connections),
                threshold=max(settings.idle_cpu_threshold, settings.idle_db_connection_threshold),
                metadata={
                    "db_instance_class": db.get("DBInstanceClass"),
                    "engine": db.get("Engine"),
                    "avg_cpu": cpu,
                    "avg_connections": connections,
                    **ownership_metadata(tags, settings),
                },
            )
        )
    return findings


def detect_idle_resources(factory: AwsClientFactory, settings: Settings) -> list[Finding]:
    return [
        *detect_idle_ec2(factory, settings),
        *detect_unattached_ebs(factory, settings),
        *detect_idle_rds(factory, settings),
    ]
