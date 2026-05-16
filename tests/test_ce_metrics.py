from __future__ import annotations

from aws_clients import ce_amount_from_keys, ce_preferred_amount, ce_row_metric_map


def test_ce_row_metric_map_prefers_total_then_metrics() -> None:
    assert ce_row_metric_map({"Total": {"BlendedCost": {"Amount": "1", "Unit": "USD"}}}) == {"BlendedCost": {"Amount": "1", "Unit": "USD"}}
    assert ce_row_metric_map({"Metrics": {"BlendedCost": {"Amount": "2", "Unit": "USD"}}}) == {"BlendedCost": {"Amount": "2", "Unit": "USD"}}
    assert ce_row_metric_map({}) == {}


def test_ce_preferred_amount_prefers_unblended_when_present() -> None:
    m = {
        "UnblendedCost": {"Amount": "1.5", "Unit": "USD"},
        "BlendedCost": {"Amount": "9", "Unit": "USD"},
    }
    assert ce_preferred_amount(m) == (1.5, "USD")


def test_ce_preferred_amount_falls_back_to_blended() -> None:
    m = {"BlendedCost": {"Amount": "104.37", "Unit": "INR"}}
    assert ce_preferred_amount(m) == (104.37, "INR")


def test_ce_preferred_amount_falls_back_to_amortized() -> None:
    m = {"AmortizedCost": {"Amount": "2", "Unit": "USD"}}
    assert ce_preferred_amount(m) == (2.0, "USD")


def test_ce_preferred_amount_empty_returns_zero_usd() -> None:
    assert ce_preferred_amount({}) == (0.0, "USD")


def test_ce_preferred_amount_skips_zero_unblended_uses_blended() -> None:
    m = {
        "UnblendedCost": {"Amount": "0", "Unit": "USD"},
        "NetUnblendedCost": {"Amount": "0", "Unit": "USD"},
        "BlendedCost": {"Amount": "1.2", "Unit": "USD"},
    }
    assert ce_preferred_amount(m) == (1.2, "USD")


def test_ce_amount_from_keys_prefers_net_amortized() -> None:
    m = {
        "NetAmortizedCost": {"Amount": "3", "Unit": "USD"},
        "AmortizedCost": {"Amount": "9", "Unit": "USD"},
    }
    assert ce_amount_from_keys(m, ("NetAmortizedCost", "AmortizedCost")) == (3.0, "USD")


def test_ce_amount_from_keys_skips_zero_net_amortized() -> None:
    m = {
        "NetAmortizedCost": {"Amount": "0", "Unit": "USD"},
        "AmortizedCost": {"Amount": "2.5", "Unit": "USD"},
    }
    assert ce_amount_from_keys(m, ("NetAmortizedCost", "AmortizedCost")) == (2.5, "USD")


def test_ce_preferred_amount_all_zero_returns_last_zero() -> None:
    m = {
        "UnblendedCost": {"Amount": "0", "Unit": "USD"},
        "BlendedCost": {"Amount": "0", "Unit": "USD"},
    }
    assert ce_preferred_amount(m) == (0.0, "USD")
