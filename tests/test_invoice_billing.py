from __future__ import annotations

from datetime import date

from invoice_billing import _rollup_period_summaries, fetch_invoice_billing


def test_rollup_period_summaries_sums_totals() -> None:
    summaries = [
        {
            "InvoiceId": "a",
            "BillingPeriod": {"Year": 2026, "Month": 4},
            "IssuedDate": 100,
            "BaseCurrencyAmount": {"TotalAmount": "10", "TotalAmountBeforeTax": "8", "CurrencyCode": "USD"},
        },
        {
            "InvoiceId": "b",
            "BillingPeriod": {"Year": 2026, "Month": 4},
            "IssuedDate": 200,
            "BaseCurrencyAmount": {"TotalAmount": "5", "TotalAmountBeforeTax": "4", "CurrencyCode": "USD"},
        },
    ]
    r = _rollup_period_summaries(summaries)
    assert r is not None
    assert r["billing_period"] == {"year": 2026, "month": 4}
    assert r["total_amount"] == 15.0
    assert r["total_before_tax"] == 12.0
    assert r["currency"] == "USD"
    assert r["display_basis"] == "base_currency"
    assert r["base_total_amount"] == 15.0
    assert r["payment_total_amount"] is None
    assert r["issued_date"] == 200
    assert set(r["invoice_ids"]) == {"a", "b"}


def test_rollup_prefers_payment_currency_when_present() -> None:
    summaries = [
        {
            "InvoiceId": "x",
            "BillingPeriod": {"Year": 2026, "Month": 3},
            "IssuedDate": 1,
            "BaseCurrencyAmount": {
                "TotalAmount": "100.00",
                "TotalAmountBeforeTax": "90.00",
                "CurrencyCode": "USD",
            },
            "PaymentCurrencyAmount": {
                "TotalAmount": "8500.50",
                "TotalAmountBeforeTax": "7650.00",
                "CurrencyCode": "INR",
            },
        }
    ]
    r = _rollup_period_summaries(summaries)
    assert r is not None
    assert r["display_basis"] == "payment_currency"
    assert r["total_amount"] == 8500.5
    assert r["currency"] == "INR"
    assert r["base_total_amount"] == 100.0
    assert r["base_currency"] == "USD"


def test_fetch_invoice_billing_disabled() -> None:
    class F:
        pass

    out = fetch_invoice_billing(F(), date(2026, 5, 1), enabled=False)
    assert out == {"available": False, "skipped": True}
