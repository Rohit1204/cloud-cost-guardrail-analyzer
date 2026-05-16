from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import boto3

# Cost Explorer may omit keys or return 0 for some metrics while another carries the charge (e.g. blended vs unblended).
_CE_METRIC_KEYS: tuple[str, ...] = (
    "UnblendedCost",
    "NetUnblendedCost",
    "BlendedCost",
    "NetAmortizedCost",
    "AmortizedCost",
)


def ce_preferred_amount(metrics: dict[str, Any]) -> tuple[float, str]:
    """Return amount and unit from the best CE metric in a Total or Group Metrics map.

    Tries metrics in order but skips an entry whose Amount parses to exactly 0 so we do not
    stick on UnblendedCost=0 when BlendedCost (or another line) reflects spend the Billing page shows.
    """
    last_non_missing: tuple[float, str] | None = None
    for key in _CE_METRIC_KEYS:
        raw = metrics.get(key)
        if not isinstance(raw, dict):
            continue
        amt = raw.get("Amount")
        if amt is None:
            amt = raw.get("amount")
        if amt in (None, ""):
            continue
        try:
            value = float(amt)
        except (TypeError, ValueError):
            continue
        unit = str(raw.get("Unit") or raw.get("unit") or "USD")
        last_non_missing = (value, unit)
        if value != 0.0:
            return value, unit
    if last_non_missing is not None:
        return last_non_missing
    return 0.0, "USD"


def ce_amount_from_keys(
    metrics: dict[str, Any],
    keys: tuple[str, ...],
    *,
    skip_zero: bool = True,
) -> tuple[float, str]:
    """Sum-style metric picker: walk keys in order; optionally skip amounts that parse to 0."""
    last_non_missing: tuple[float, str] | None = None
    for key in keys:
        raw = metrics.get(key)
        if not isinstance(raw, dict):
            continue
        amt = raw.get("Amount")
        if amt is None:
            amt = raw.get("amount")
        if amt in (None, ""):
            continue
        try:
            value = float(amt)
        except (TypeError, ValueError):
            continue
        unit = str(raw.get("Unit") or raw.get("unit") or "USD")
        last_non_missing = (value, unit)
        if skip_zero and value == 0.0:
            continue
        return value, unit
    if last_non_missing is not None:
        return last_non_missing
    return 0.0, "USD"


def ce_row_metric_map(row: dict[str, Any]) -> dict[str, Any]:
    """Metric map from a GetCostAndUsage ResultsByTime row (Total or top-level Metrics)."""
    total = row.get("Total")
    if isinstance(total, dict) and total:
        return total
    metrics = row.get("Metrics")
    if isinstance(metrics, dict) and metrics:
        return metrics
    return {}


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

    @property
    def sts(self) -> Any:
        return self.client("sts", region_name="us-east-1")

    @property
    def invoicing(self) -> Any:
        # AWS Invoicing / invoice summary API uses the global us-east-1 endpoint.
        return self.client("invoicing", region_name="us-east-1")

    def aws_account_id(self) -> str:
        aid = self.sts.get_caller_identity().get("Account")
        if not aid:
            raise RuntimeError("STS GetCallerIdentity did not return Account")
        return str(aid)

    def list_invoice_summaries_for_billing_period(
        self, *, account_id: str, year: int, month: int
    ) -> list[dict[str, Any]]:
        selector = {"ResourceType": "ACCOUNT_ID", "Value": account_id}
        filt = {"BillingPeriod": {"Year": year, "Month": month}}
        items: list[dict[str, Any]] = []
        token: str | None = None
        while True:
            kwargs: dict[str, Any] = {
                "Selector": selector,
                "Filter": filt,
                "MaxResults": 100,
            }
            if token:
                kwargs["NextToken"] = token
            resp = self.invoicing.list_invoice_summaries(**kwargs)
            items.extend(resp.get("InvoiceSummaries") or [])
            token = resp.get("NextToken")
            if not token:
                break
        return items

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
            "Metrics": list(_CE_METRIC_KEYS),
        }
        if group_by_service:
            kwargs["GroupBy"] = [{"Type": "DIMENSION", "Key": "SERVICE"}]

        merged: dict[tuple[str, str], dict[str, Any]] = {}
        token: str | None = None
        while True:
            page_kwargs = dict(kwargs)
            if token:
                page_kwargs["NextPageToken"] = token
            resp = self.ce.get_cost_and_usage(**page_kwargs)
            for row in resp.get("ResultsByTime", []):
                tp = row.get("TimePeriod") or {}
                key = (str(tp.get("Start") or ""), str(tp.get("End") or ""))
                existing = merged.get(key)
                if existing is None:
                    merged[key] = row
                else:
                    g0 = existing.get("Groups") or []
                    g1 = row.get("Groups") or []
                    if g1:
                        existing["Groups"] = g0 + g1
                    t0, t1 = existing.get("Total"), row.get("Total")
                    if (not isinstance(t0, dict) or not t0) and isinstance(t1, dict) and t1:
                        existing["Total"] = t1
                    m0, m1 = existing.get("Metrics"), row.get("Metrics")
                    if (not isinstance(m0, dict) or not m0) and isinstance(m1, dict) and m1:
                        existing["Metrics"] = m1
            token = resp.get("NextPageToken")
            if not token:
                break

        return sorted(merged.values(), key=lambda r: (r.get("TimePeriod") or {}).get("Start") or "")

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
