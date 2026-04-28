from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import boto3


class AwsClientFactory:
    def __init__(self, region_name: str) -> None:
        self.region_name = region_name
        self._clients: dict[str, Any] = {}

    def client(self, service_name: str, *, region_name: str | None = None) -> Any:
        key = f"{service_name}:{region_name or self.region_name}"
        if key not in self._clients:
            self._clients[key] = boto3.client(service_name, region_name=region_name or self.region_name)
        return self._clients[key]

    @property
    def ec2(self) -> Any:
        return self.client("ec2")

    @property
    def rds(self) -> Any:
        return self.client("rds")

    @property
    def cloudwatch(self) -> Any:
        return self.client("cloudwatch")

    @property
    def ce(self) -> Any:
        # Cost Explorer is a global endpoint exposed through us-east-1.
        return self.client("ce", region_name="us-east-1")

    def list_running_instances(self) -> list[dict[str, Any]]:
        paginator = self.ec2.get_paginator("describe_instances")
        instances: list[dict[str, Any]] = []
        for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
            for reservation in page.get("Reservations", []):
                instances.extend(reservation.get("Instances", []))
        return instances

    def list_unattached_volumes(self) -> list[dict[str, Any]]:
        paginator = self.ec2.get_paginator("describe_volumes")
        volumes: list[dict[str, Any]] = []
        for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
            volumes.extend(page.get("Volumes", []))
        return volumes

    def list_rds_instances(self) -> list[dict[str, Any]]:
        paginator = self.rds.get_paginator("describe_db_instances")
        instances: list[dict[str, Any]] = []
        for page in paginator.paginate():
            instances.extend(page.get("DBInstances", []))
        return instances

    def rds_tags(self, resource_arn: str | None) -> list[dict[str, str]]:
        if not resource_arn:
            return []
        return self.rds.list_tags_for_resource(ResourceName=resource_arn).get("TagList", [])

    def average_metric(
        self,
        *,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]],
        lookback_days: int,
        statistic: str = "Average",
    ) -> float | None:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=lookback_days)
        response = self.cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=[statistic],
        )
        datapoints = response.get("Datapoints", [])
        values = [float(point[statistic]) for point in datapoints if statistic in point]
        if not values:
            return None
        return sum(values) / len(values)

    def unblended_costs(
        self,
        *,
        start: str,
        end: str,
        granularity: str,
        group_by_service: bool = False,
    ) -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "TimePeriod": {"Start": start, "End": end},
            "Granularity": granularity,
            "Metrics": ["UnblendedCost"],
        }
        if group_by_service:
            kwargs["GroupBy"] = [{"Type": "DIMENSION", "Key": "SERVICE"}]
        return self.ce.get_cost_and_usage(**kwargs).get("ResultsByTime", [])

    def daily_unblended_costs(self, *, start: str, end: str, group_by_service: bool = False) -> list[dict[str, Any]]:
        return self.unblended_costs(
            start=start,
            end=end,
            granularity="DAILY",
            group_by_service=group_by_service,
        )

    def monthly_unblended_costs(self, *, start: str, end: str, group_by_service: bool = False) -> list[dict[str, Any]]:
        return self.unblended_costs(
            start=start,
            end=end,
            granularity="MONTHLY",
            group_by_service=group_by_service,
        )
