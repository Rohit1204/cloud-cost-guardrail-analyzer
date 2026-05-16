from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


def _prior_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _fin_amount(x: float | None) -> float | None:
    if x is None:
        return None
    return float(round(x + 0.0, 4))


def _fin_invoice_amount(x: float | None) -> float | None:
    """Match AWS invoice strings more closely than 4dp CE rounding."""
    if x is None:
        return None
    return float(round(x + 0.0, 6))


def _parse_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _rollup_period_summaries(summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not summaries:
        return None
    base_totals: list[float] = []
    base_befores: list[float] = []
    base_currency: str | None = None
    pay_totals: list[float] = []
    pay_befores: list[float] = []
    pay_currency: str | None = None
    tax_totals: list[float] = []
    tax_currency: str | None = None
    invoice_ids: list[str] = []
    issued_dates: list[int] = []
    bp_year: int | None = None
    bp_month: int | None = None

    for inv in summaries:
        bp = inv.get("BillingPeriod") or {}
        if isinstance(bp, dict):
            y, m = bp.get("Year"), bp.get("Month")
            if isinstance(y, int):
                bp_year = y
            if isinstance(m, int):
                bp_month = m
        base = inv.get("BaseCurrencyAmount") or {}
        if isinstance(base, dict):
            t = _parse_float(base.get("TotalAmount"))
            if t is not None:
                base_totals.append(t)
            bt = _parse_float(base.get("TotalAmountBeforeTax"))
            if bt is not None:
                base_befores.append(bt)
            cur = base.get("CurrencyCode")
            if cur:
                base_currency = str(cur)
        pay = inv.get("PaymentCurrencyAmount") or {}
        if isinstance(pay, dict):
            pt = _parse_float(pay.get("TotalAmount"))
            if pt is not None:
                pay_totals.append(pt)
            pbt = _parse_float(pay.get("TotalAmountBeforeTax"))
            if pbt is not None:
                pay_befores.append(pbt)
            pcur = pay.get("CurrencyCode")
            if pcur:
                pay_currency = str(pcur)
        tax_block = inv.get("TaxCurrencyAmount") or {}
        if isinstance(tax_block, dict):
            tt = _parse_float(tax_block.get("TotalAmount"))
            if tt is not None:
                tax_totals.append(tt)
            tcur = tax_block.get("CurrencyCode")
            if tcur:
                tax_currency = str(tcur)
        iid = inv.get("InvoiceId")
        if iid:
            invoice_ids.append(str(iid))
        idt = inv.get("IssuedDate")
        if isinstance(idt, int):
            issued_dates.append(idt)

    base_total_amount = _fin_invoice_amount(sum(base_totals)) if base_totals else None
    base_total_before_tax = _fin_invoice_amount(sum(base_befores)) if base_befores else None
    payment_total_amount = _fin_invoice_amount(sum(pay_totals)) if pay_totals else None
    payment_total_before_tax = _fin_invoice_amount(sum(pay_befores)) if pay_befores else None
    tax_total_amount = _fin_invoice_amount(sum(tax_totals)) if tax_totals else None
    issued_date = max(issued_dates) if issued_dates else None

    if bp_year is None or bp_month is None:
        return None

    # Billing console "amount charged" often follows payment currency when AWS provides it.
    if payment_total_amount is not None:
        display_total = payment_total_amount
        display_before_tax = payment_total_before_tax
        display_currency = pay_currency or base_currency
        display_basis = "payment_currency"
    else:
        display_total = base_total_amount
        display_before_tax = base_total_before_tax
        display_currency = base_currency
        display_basis = "base_currency"

    return {
        "billing_period": {"year": bp_year, "month": bp_month},
        "invoice_ids": invoice_ids,
        "total_amount": display_total,
        "total_before_tax": display_before_tax,
        "currency": display_currency,
        "display_basis": display_basis,
        "base_total_amount": base_total_amount,
        "base_total_before_tax": base_total_before_tax,
        "base_currency": base_currency,
        "payment_total_amount": payment_total_amount,
        "payment_total_before_tax": payment_total_before_tax,
        "payment_currency": pay_currency,
        "tax_currency_total_amount": tax_total_amount,
        "tax_currency": tax_currency,
        "issued_date": issued_date,
    }


def fetch_invoice_billing(factory: Any, today: date, *, enabled: bool) -> dict[str, Any]:
    """Load AWS Invoice Summary API data for the current and prior calendar billing months.

    The current month often has no issued invoice until the period closes; ``prior_period`` is the
    usual place to find an authoritative total that matches the Billing console invoice.
    """
    if not enabled:
        return {"available": False, "skipped": True}

    try:
        account_id = factory.aws_account_id()
    except Exception as exc:
        logger.info("invoice_billing: could not resolve AWS account: %s", exc)
        return {"available": False, "error": {"error_type": type(exc).__name__, "message": str(exc)}}

    cy, cm = today.year, today.month
    py, pm = _prior_month(cy, cm)

    out: dict[str, Any] = {
        "available": True,
        "skipped": False,
        "account_id": account_id,
        "source": "aws_invoicing_list_invoice_summaries",
    }

    try:
        cur_raw = factory.list_invoice_summaries_for_billing_period(account_id=account_id, year=cy, month=cm)
        prior_raw = factory.list_invoice_summaries_for_billing_period(account_id=account_id, year=py, month=pm)
    except Exception as exc:
        logger.info("invoice_billing: ListInvoiceSummaries failed: %s", exc)
        out["error"] = {"error_type": type(exc).__name__, "message": str(exc)}
        return out

    out["current_period"] = _rollup_period_summaries(cur_raw)
    out["prior_period"] = _rollup_period_summaries(prior_raw)
    return out
